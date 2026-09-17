import os

import requests
import streamlit as st
from dotenv import load_dotenv
from requests.exceptions import RequestException

load_dotenv()

API_URL = os.getenv(
    "API_URL",
    "http://localhost:8000"
).rstrip("/")

st.set_page_config(
    page_title="Support Decision Assistant",
    page_icon="🎧",
    layout="wide"
)

st.title("Support Decision Assistant")
st.caption(
    "Turn customer issues into consistent, policy-aware next steps."
)

for key, default in {
    "token": None,
    "email": "",
    "auth_mode": "Log in",
    "pending_email": "",
    "pending_password": "",
    "auth_message": "",
    "clear_ticket_form": False,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


def error_detail(response: requests.Response) -> str:
    try:
        payload = response.json()
        detail = payload.get("detail", payload)

        if isinstance(detail, list):
            return "; ".join(
                str(item.get("msg", item))
                for item in detail
            )

        return str(detail)

    except ValueError:
        return (
            response.text
            or f"Request failed with status {response.status_code}"
        )


def api_request(
    method: str,
    path: str,
    timeout: int = 180,
    **kwargs
):
    headers = kwargs.pop("headers", {})

    if st.session_state.token:
        headers["Authorization"] = (
            f"Bearer {st.session_state.token}"
        )

    try:
        response = requests.request(
            method,
            f"{API_URL}{path}",
            headers=headers,
            timeout=timeout,
            **kwargs
        )

    except RequestException as error:
        raise RuntimeError(
            f"Could not reach the API at {API_URL}. "
            f"Is uvicorn running? {error}"
        ) from error

    if not response.ok:
        raise RuntimeError(error_detail(response))

    return response.json()


if not st.session_state.token:

    if st.session_state.pop("switch_to_login", False):
        st.session_state.auth_mode = "Log in"
        st.session_state.login_email = ""

    st.radio(
        "Account",
        ["Log in", "Create account"],
        key="auth_mode",
        horizontal=True
    )

    if st.session_state.auth_message:
        st.success(
            st.session_state.auth_message
        )

    if st.session_state.auth_mode == "Log in":

        with st.form("login"):

            email = st.text_input(
                "Email",
                key="login_email"
            )

            password = st.text_input(
                "Password",
                type="password",
                key="login_password"
            )

            submitted = st.form_submit_button(
                "Log in",
                type="primary"
            )

        if submitted:

            try:

                result = api_request(
                    "POST",
                    "/auth/login",
                    data={
                        "username": email,
                        "password": password
                    },
                    timeout=30
                )

                st.session_state.token = result["access_token"]
                st.session_state.email = email
                st.session_state.pending_password = ""
                st.session_state.auth_message = ""

                st.rerun()

            except RuntimeError as error:
                st.error(str(error))

    else:

        with st.form("register"):

            email = st.text_input("Email")

            password = st.text_input(
                "Password",
                type="password"
            )

            confirm = st.text_input(
                "Confirm password",
                type="password"
            )

            submitted = st.form_submit_button(
                "Create account",
                type="primary"
            )

        if submitted:

            if password != confirm:

                st.error("Passwords do not match.")

            else:

                try:

                    api_request(
                        "POST",
                        "/auth/register",
                        json={
                            "email": email,
                            "password": password
                        },
                        timeout=30
                    )

                    st.session_state.pending_email = ""
                    st.session_state.pending_password = ""
                    st.session_state.switch_to_login = True
                    st.session_state.auth_message = (
                        "Account created. Please log in."
                    )

                    st.rerun()

                except RuntimeError as error:
                    st.error(str(error))

    st.stop()


with st.sidebar:

    st.write(
        f"Signed in as **{st.session_state.email}**"
    )

    if st.button("Log out"):

        st.session_state.token = None
        st.session_state.email = ""
        st.session_state.pending_password = ""
        st.session_state.login_password = ""
        st.session_state.auth_message = ""

        st.rerun()

    view = st.radio(
        "View",
        ["New ticket", "History"]
    )


if view == "New ticket":

    st.header("New ticket")

    if "ticket_form_version" not in st.session_state:
        st.session_state.ticket_form_version = 0

    form_key = f"ticket_form_{st.session_state.ticket_form_version}"

    with st.form(form_key):

        subject = st.text_input(
            "Subject",
            placeholder="Item arrived damaged"
        )

        description = st.text_area(
            "Customer message",
            height=180,
            placeholder="Include the order number and relevant details."
        )

        col1, col2 = st.columns([1, 1])

        with col1:
            submitted = st.form_submit_button(
                "Analyze ticket",
                type="primary"
            )

        with col2:
            add_another = st.form_submit_button(
                "Add another ticket"
            )

    if add_another:
        st.session_state.ticket_form_version += 1
        st.rerun()

    if submitted:

        if not subject.strip():

            st.error("Please enter a subject.")

        elif not description.strip():

            st.error("Please enter the customer message.")

        else:

            try:

                with st.spinner("Analyzing ticket..."):

                    ticket = api_request(
                        "POST",
                        "/tickets",
                        json={
                            "subject": subject,
                            "description": description
                        }
                    )

                decision = ticket["decision"]

                st.success("Ticket analyzed")

                st.metric(
                    "Recommended action",
                    decision["action"]
                )

                st.write(
                    decision["reason"]
                )

                confidence = decision.get(
                    "confidence",
                    0
                )

                confidence = min(
                    max(float(confidence), 0.0),
                    1.0
                )

                st.progress(
                    confidence,
                    text=f"Confidence: {confidence:.0%}"
                )

                sources = decision.get(
                    "sources",
                    []
                )

                st.caption(
                    "Sources: "
                    + (
                        ", ".join(sources)
                        if sources
                        else "No policy source"
                    )
                )

            except RuntimeError as error:

                st.error(str(error))

if view == "History":

    st.header("Ticket History")

    try:

        tickets = api_request(
            "GET",
            "/tickets",
            timeout=30
        )

        if not tickets:

            st.info(
                "No tickets found."
            )

        else:

            st.write(
                f"**{len(tickets)} ticket(s) found**"
            )

            for ticket in tickets:

                ticket_id = ticket.get(
                    "id",
                    "Unknown"
                )

                subject = ticket.get(
                    "subject",
                    "Untitled ticket"
                )

                description = ticket.get(
                    "description",
                    ""
                )

                created_at = ticket.get(
                    "created_at",
                    "Unknown"
                )

                decision = ticket.get(
                    "decision"
                )

                with st.expander(
                    f"Ticket #{ticket_id} — {subject}"
                ):

                    st.subheader(
                        "Ticket message"
                    )

                    st.write(
                        description
                    )

                    st.subheader(
                        "Decision"
                    )

                    if decision:

                        action = decision.get(
                            "action",
                            "Unknown"
                        )

                        confidence = decision.get(
                            "confidence",
                            0
                        )

                        reason = decision.get(
                            "reason",
                            "No reason provided."
                        )

                        sources = decision.get(
                            "sources",
                            []
                        )

                        st.write(
                            f"**Action:** {action}"
                        )

                        try:

                            confidence = min(
                                max(
                                    float(confidence),
                                    0.0
                                ),
                                1.0
                            )

                            st.progress(
                                confidence,
                                text=(
                                    f"Confidence: "
                                    f"{confidence:.0%}"
                                )
                            )

                        except (
                            TypeError,
                            ValueError
                        ):

                            st.write(
                                f"**Confidence:** {confidence}"
                            )

                        st.write(
                            f"**Reason:** {reason}"
                        )

                        st.write(
                            "**Sources:** "
                            + (
                                ", ".join(sources)
                                if sources
                                else "No policy source"
                            )
                        )

                    else:

                        st.info(
                            "No decision available "
                            "for this ticket."
                        )

                    st.caption(
                        f"Created: {created_at}"
                    )

    except RuntimeError as error:

        st.error(
            f"Could not load ticket history: {error}"
        )