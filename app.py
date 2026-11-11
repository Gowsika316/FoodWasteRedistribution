
import streamlit as st
import pandas as pd
from datetime import datetime, date, time

from database import (
    initialize_db,
    get_donors,
    add_donation,
    get_available_donations,
    get_all_donations,
    get_donations_by_donor,
    get_donations_by_collector,
    get_donor_id_for_user,
    edit_donation_by_donor,
    delete_donation_by_donor,
    claim_donation_by_collector,
    update_collection_by_collector
)

from accounts import (
    initialize_accounts,
    register_account,
    login_account
)

from priority_queue import prioritize_donations


# -----------------------------------------
# 1. APPLICATION CONFIGURATION
# -----------------------------------------

st.set_page_config(
    page_title="Food Waste Redistribution",
    page_icon="🍱",
    layout="wide"
)

initialize_db()
initialize_accounts()


# -----------------------------------------
# 2. SESSION MANAGEMENT
# -----------------------------------------

if "user" not in st.session_state:
    st.session_state.user = None


def logout():
    st.session_state.user = None
    st.rerun()


# -----------------------------------------
# 3. LOGIN AND REGISTRATION
# -----------------------------------------

if st.session_state.user is None:

    st.title("🍱 Food Waste Redistribution Platform")

    st.write(
        "Connecting food donors with NGOs to reduce food waste."
    )

    login_tab, register_tab = st.tabs(
        ["Login", "Create Account"]
    )

    # LOGIN
    with login_tab:

        st.subheader("Welcome Back")

        with st.form("login_form"):

            username = st.text_input("Username")
            password = st.text_input(
                "Password",
                type="password"
            )

            submitted = st.form_submit_button("Login")

            if submitted:

                user = login_account(username, password)

                if user:

                    st.session_state.user = user
                    st.rerun()

                else:

                    st.error("Invalid username or password.")

    # REGISTRATION
    with register_tab:

        st.subheader("Create Your Account")

        with st.form("register_form"):

            role = st.selectbox(
                "Account Type",
                ["Donor", "Collector (NGO)"]
            )

            display_name = st.text_input(
                "Restaurant / NGO Name"
            )

            username = st.text_input("Choose Username")

            password = st.text_input(
                "Choose Password",
                type="password"
            )

            confirm_password = st.text_input(
                "Confirm Password",
                type="password"
            )

            location = st.text_input("Location")
            phone = st.text_input("Phone Number")

            submitted = st.form_submit_button(
                "Create Account"
            )

            if submitted:

                if not all([
                    display_name.strip(),
                    username.strip(),
                    location.strip(),
                    password,
                    confirm_password
                ]):

                    st.error("Please fill in all required fields.")

                elif password != confirm_password:

                    st.error("Passwords do not match.")

                else:

                    role_value = (
                        "donor"
                        if role == "Donor"
                        else "collector"
                    )

                    success, message = register_account(
                        username,
                        password,
                        role_value,
                        display_name,
                        location,
                        phone
                    )

                    if success:

                        st.success(
                            message + " Please log in."
                        )

                    else:

                        st.error(message)


# -----------------------------------------
# 4. LOGGED-IN USER DASHBOARD
# -----------------------------------------

else:

    user = st.session_state.user

    user_id = user["user_id"]
    role = user["role"]
    display_name = user["display_name"]

    st.sidebar.title("My Account")

    st.sidebar.write(f"**{display_name}**")

    st.sidebar.caption(
        f"Account type: {role.title()}"
    )

    if st.sidebar.button("Logout"):
        logout()

    st.title("🍱 Food Waste Redistribution Platform")

    # -------------------------------------
    # DONOR DASHBOARD
    # -------------------------------------

    if role == "donor":

        menu = [
            "My Dashboard",
            "Add Food Donation",
            "My Donations",
            "Available Food"
        ]

        page = st.sidebar.selectbox(
            "Navigation",
            menu
        )

        my_donations = get_donations_by_donor(user_id)

        if page == "My Dashboard":

            st.header("Donor Dashboard")

            total = len(my_donations)

            available = sum(
                d["status"] == "Available"
                for d in my_donations
            )

            claimed = sum(
                d["status"] == "Claimed"
                for d in my_donations
            )

            collected = sum(
                d["status"] == "Collected"
                for d in my_donations
            )

            c1, c2, c3, c4 = st.columns(4)

            c1.metric("My Donations", total)
            c2.metric("Available", available)
            c3.metric("Claimed", claimed)
            c4.metric("Collected", collected)

            st.subheader("My Recent Donations")

            if my_donations:
                st.dataframe(
                    pd.DataFrame(my_donations),
                    use_container_width=True
                )
            else:
                st.info("You haven't added any donations yet.")

        # ---------------------------------
        # ADD FOOD DONATION
        # ---------------------------------

        elif page == "Add Food Donation":

            st.header("Add Food Donation")

            donor_id = get_donor_id_for_user(user_id)

            if donor_id is None:

                st.error(
                    "Your donor profile is not linked to your account."
                )

            else:

                with st.form("add_donation_form"):

                    food_name = st.text_input("Food Name")

                    quantity = st.number_input(
                        "Quantity",
                        min_value=0.1,
                        value=1.0,
                        step=0.5
                    )

                    unit = st.selectbox(
                        "Unit",
                        ["Packets", "Kg", "Litres", "Pieces"]
                    )

                    expiry_date = st.date_input(
                        "Collection / Expiry Deadline Date",
                        value=date.today(),
                        min_value=date.today()
                    )

                    expiry_time = st.time_input(
                        "Deadline Time",
                        value=time(18, 0)
                    )

                    submitted = st.form_submit_button(
                        "Add Donation"
                    )

                    if submitted:

                        deadline = datetime.combine(
                            expiry_date,
                            expiry_time
                        )

                        if not food_name.strip():

                            st.error("Enter the food name.")

                        elif deadline <= datetime.now():

                            st.error(
                                "Please select a future deadline."
                            )

                        else:

                            success = add_donation(
                                donor_id,
                                food_name.strip(),
                                quantity,
                                unit,
                                deadline
                            )

                            if success:
                                st.success(
                                    "Donation added successfully!"
                                )
                            else:
                                st.warning(
                                    "This exact donation already exists."
                                )

        # ---------------------------------
        # MY DONATIONS: EDIT AND DELETE
        # ---------------------------------

        elif page == "My Donations":

            st.header("Manage My Donations")

            if not my_donations:

                st.info("You haven't added any donations yet.")

            else:

                st.dataframe(
                    pd.DataFrame(my_donations),
                    use_container_width=True
                )

                editable = [
                    d for d in my_donations
                    if d["status"] == "Available"
                ]

                if editable:

                    donation_map = {
                        d["donation_id"]: d
                        for d in editable
                    }

                    st.subheader("Edit My Donation")

                    selected_id = st.selectbox(
                        "Choose donation to edit",
                        list(donation_map.keys()),
                        format_func=lambda x: (
                            f'{x} - {donation_map[x]["food_name"]}'
                        )
                    )

                    selected = donation_map[selected_id]

                    with st.form("edit_donation_form"):

                        new_food = st.text_input(
                            "Food Name",
                            value=selected["food_name"]
                        )

                        new_quantity = st.number_input(
                            "Quantity",
                            min_value=0.1,
                            value=float(selected["quantity"]),
                            step=0.5
                        )

                        units = [
                            "Packets", "Kg", "Litres", "Pieces"
                        ]

                        current_unit = selected["unit"]

                        unit_index = (
                            units.index(current_unit)
                            if current_unit in units else 0
                        )

                        new_unit = st.selectbox(
                            "Unit",
                            units,
                            index=unit_index
                        )

                        old_deadline = datetime.fromisoformat(
                            selected["expiry_time"]
                        )

                        new_date = st.date_input(
                            "Deadline Date",
                            value=old_deadline.date()
                        )

                        new_time = st.time_input(
                            "Deadline Time",
                            value=old_deadline.time()
                        )

                        submitted = st.form_submit_button(
                            "Save Changes"
                        )

                        if submitted:

                            deadline = datetime.combine(
                                new_date,
                                new_time
                            )

                            if not new_food.strip():
                                st.error("Enter the food name.")

                            elif deadline <= datetime.now():
                                st.error(
                                    "Deadline must be in the future."
                                )

                            else:

                                success = edit_donation_by_donor(
                                    selected_id,
                                    user_id,
                                    new_food,
                                    new_quantity,
                                    new_unit,
                                    deadline
                                )

                                if success:
                                    st.success(
                                        "Donation updated successfully!"
                                    )
                                    st.rerun()
                                else:
                                    st.error(
                                        "Unable to edit this donation."
                                    )

                    st.subheader("Delete My Donation")

                    delete_id = st.selectbox(
                        "Choose donation to delete",
                        list(donation_map.keys()),
                        format_func=lambda x: (
                            f'{x} - {donation_map[x]["food_name"]}'
                        ),
                        key="delete_donation_select"
                    )

                    if st.button("Delete Donation"):

                        success = delete_donation_by_donor(
                            delete_id,
                            user_id
                        )

                        if success:
                            st.success("Donation deleted!")
                            st.rerun()
                        else:
                            st.error(
                                "Unable to delete this donation."
                            )

                else:

                    st.info(
                        "You can edit or delete only donations "
                        "that have not been claimed."
                    )

        # ---------------------------------
        # AVAILABLE FOOD FOR DONORS
        # ---------------------------------

        elif page == "Available Food":

            st.header("Available Food Donations")

            donations = prioritize_donations(
                get_available_donations()
            )

            if donations:

                st.dataframe(
                    pd.DataFrame(donations),
                    use_container_width=True
                )

            else:

                st.info("No available donations right now.")

    # -------------------------------------
    # COLLECTOR DASHBOARD
    # -------------------------------------

    elif role == "collector":

        menu = [
            "My Dashboard",
            "Available Food",
            "My Collections"
        ]

        page = st.sidebar.selectbox(
            "Navigation",
            menu
        )

        my_collections = get_donations_by_collector(user_id)

        if page == "My Dashboard":

            st.header("Collector Dashboard")

            total = len(my_collections)

            claimed = sum(
                d["status"] == "Claimed"
                for d in my_collections
            )

            collected = sum(
                d["status"] == "Collected"
                for d in my_collections
            )

            cancelled = sum(
                d["status"] == "Cancelled"
                for d in my_collections
            )

            c1, c2, c3, c4 = st.columns(4)

            c1.metric("My Claims", total)
            c2.metric("In Progress", claimed)
            c3.metric("Collected", collected)
            c4.metric("Cancelled", cancelled)

            st.subheader("My Recent Collections")

            if my_collections:

                st.dataframe(
                    pd.DataFrame(my_collections),
                    use_container_width=True
                )

            else:

                st.info("You haven't claimed any donations yet.")

        # ---------------------------------
        # AVAILABLE FOOD
        # ---------------------------------

        elif page == "Available Food":

            st.header("Available Food Donations")

            donations = prioritize_donations(
                get_available_donations()
            )

            if not donations:

                st.info("No available donations right now.")

            else:

                display_data = []

                for d in donations:

                    display_data.append({
                        "Donation ID": d["donation_id"],
                        "Food": d["food_name"],
                        "Quantity": (
                            f'{d["quantity"]} {d["unit"]}'
                        ),
                        "Donor": d["donor_name"],
                        "Location": d["location"],
                        "Deadline": d["expiry_time"]
                    })

                st.dataframe(
                    pd.DataFrame(display_data),
                    use_container_width=True
                )

                donation_map = {
                    d["donation_id"]: d["food_name"]
                    for d in donations
                }

                with st.form("claim_form"):

                    selected_id = st.selectbox(
                        "Select Donation",
                        list(donation_map.keys()),
                        format_func=lambda x: (
                            f'ID {x} - {donation_map[x]}'
                        )
                    )

                    submitted = st.form_submit_button(
                        "Claim Food"
                    )

                    if submitted:

                        success = claim_donation_by_collector(
                            selected_id,
                            user_id,
                            display_name
                        )

                        if success:

                            st.success(
                                "Donation claimed successfully!"
                            )
                            st.rerun()

                        else:

                            st.error(
                                "This donation is no longer available."
                            )

        # ---------------------------------
        # MY COLLECTIONS
        # ---------------------------------

        elif page == "My Collections":

            st.header("My Collections")

            if not my_collections:

                st.info("You haven't claimed any donations yet.")

            else:

                st.dataframe(
                    pd.DataFrame(my_collections),
                    use_container_width=True
                )

                claimed = [
                    d for d in my_collections
                    if d["status"] == "Claimed"
                ]

                if claimed:

                    claimed_map = {
                        d["donation_id"]: d["food_name"]
                        for d in claimed
                    }

                    with st.form("collection_status_form"):

                        selected_id = st.selectbox(
                            "Select Your Claimed Donation",
                            list(claimed_map.keys()),
                            format_func=lambda x: (
                                f'ID {x} - {claimed_map[x]}'
                            )
                        )

                        new_status = st.selectbox(
                            "Update Status",
                            ["Collected", "Cancelled"]
                        )

                        submitted = st.form_submit_button(
                            "Update Collection"
                        )

                        if submitted:

                            success = update_collection_by_collector(
                                selected_id,
                                user_id,
                                new_status
                            )

                            if success:

                                st.success(
                                    f"Status updated to {new_status}!"
                                )
                                st.rerun()

                            else:

                                st.error(
                                    "Unable to update this collection."
                                )

                else:

                    st.info(
                        "You have no collections waiting for an update."
                    )


# -----------------------------------------
# FOOTER
# -----------------------------------------

st.sidebar.markdown("---")
st.sidebar.caption(
    "Food Waste Redistribution Platform"
)
