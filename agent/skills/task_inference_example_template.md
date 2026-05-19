"""
agents/skills/task_inference_example_template.md — An example of an inference given previous information.

This is a template of what task_inference_example.md (a file showing a correct inference task by the user) should contain.
"""

SAMPLE_NOTES = [
    {
        "title": "MM/DD/YYYY",
        "date": "YYYY-MM-DD",
        "text": (
            "some-text"
            "more-text"
            "even-more-text"
        )
    }
]

SAMPLE_EMAILS = [
    {
        "date": "Mon, Apr 1, 2020, 11:59 PM",
        "sender": "Joe Doe <joe.doe@gmail.com>",
        "subject": "Woops",
        "body": (
            "Hi everyone," 
            "I messed up" 
        )
    },
    {
        "date": "Tue, Apr 2, 2020, 12:13 AM",
        "sender": "Alice Malice <alice.malice@gmail.com>",
        "subject": "Re: Woops",
        "body": (
            "I will give the presentation
            "See you tomorrow"
        )
    },
]

PREVIOUS_AGENDA = [
    {
        "title": "09/04/25",
        "date": "2025-09-04",
        "text": (
            "# Clinton Hall at 7 p.m. CST \n\n\n"
            "## Outline of main goals for this meeting (<5 mins)\n\n"
            "- Do stuff \n"
            "## Brainstorming (60 mins) \n\n"
            "- Come up with deck ideas to present to investors \n"
        )
    }
]

INFERRED_AGENDA = [
    {
        "title": "MM/DD/YYYY",
        "date": "YYYY-MM-DD",
        "text": (
            "blah"
        )
    }
]