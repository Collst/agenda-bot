"""
tests/fixtures/data.py — Static fixture data used across unit and integration tests.

These represent realistic (anonymised) content so tests reflect real
usage patterns rather than toy inputs.
"""

SAMPLE_NOTES = [
    {
        "title": "03/25/26",
        "date": "2026-03-25",
        "text": (
            "Attendance: Chair (Alex), Jane, Marcus, Priya\n\n"
            "1. Director Recruitment\n"
            "Alex is recruiting three directors for the spring season. "
            "Two have been contacted; one has confirmed. "
            "ACTION: Alex to confirm the remaining two directors by mid-April.\n\n"
            "2. Venue\n"
            "Jane reported the main hall is booked for all spring dates. "
            "ACTION: Jane to send confirmation emails to all directors.\n\n"
            "3. Budget\n"
            "Marcus presented the draft budget. Discussion deferred to next meeting. "
            "ACTION: Committee to review budget document before April meeting.\n\n"
            "4. Volunteer Coordination\n"
            "Priya raised the need for front-of-house volunteers. "
            "ACTION: Priya to draft a volunteer call-out email."
        ),
    }
]

SAMPLE_AGENDAS = [
    {
        "title": "02/24/26",
        "date": "2026-02-24",
        "text": (
            "THEATRE COMMITTEE MEETING\n"
            "Date: February 24, 2026 | Time: 7:00 PM | Location: Green Room\n\n"
            "1. Call to Order\n\n"
            "2. Updates\n"
            "   2.1 Alex to update on director recruitment.\n"
            "   2.2 Jane to update on venue bookings.\n\n"
            "3. Discussion\n"
            "   3.1 Discussion: Season budget review.\n\n"
            "4. New Business\n\n"
            "5. Adjournment\n"
        ),
    }
]

SAMPLE_EMAILS = [
    {
        "date": "Mon, 30 Mar 2026 09:14:00 +0000",
        "sender": "Priya <priya@example.com>",
        "subject": "Volunteer call-out draft",
        "body": (
            "Hi all, I've drafted the volunteer call-out email and sent it to "
            "our mailing list this morning. We already have 6 sign-ups. "
            "I'll have a full count before the April meeting."
        ),
    },
    {
        "date": "Wed, 1 Apr 2026 14:22:00 +0000",
        "sender": "Alex <alex@example.com>",
        "subject": "Re: Director recruitment",
        "body": (
            "Quick update — I've now confirmed all three directors. "
            "Contracts sent to Marcus for budget tracking."
        ),
    },
]

# Expected task statuses after inference on the above fixtures
EXPECTED_TASK_STATUSES = {
    "director recruitment": "complete",     # Alex confirmed in email
    "venue confirmation emails": "unresolved",  # no follow-up from Jane
    "budget review": "unresolved",          # only flagged for committee review
    "volunteer call-out": "in_progress",    # Priya sent it, count pending
}
