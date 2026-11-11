"""FAQ entries derived from the supplied handbooks. Each answer is the handbook's own wording (or a close
paraphrase) and carries the PDF page it was verified on. `python verify_faq.py` re-checks every `evidence`
sentence against the PDF text, so no entry can drift away from the documents."""
from config import COMBINED_PDF_NAME
from document_loader import handbook_for_page

# (category, question, answer, evidence phrase found verbatim in the PDF, PDF page)
_ENTRIES = [
    ("Admission and Enrollment", "What is the last day of enrolment without a fine?",
     "The last day of enrolment without fine is the first day of regular classes.",
     "The last day of enrolment without fine is the first day of regular classes.", 34),
    ("Admission and Enrollment", "What happens if a student enrolls after the last day without a fine?",
     "A student who is allowed to enroll after that date is considered a late enrollee and is subject to the late enrolment fine.",
     "Any student who is allowed to enroll after the said date shall be considered as a late enrollee", 34),
    ("Admission and Enrollment", "When is a student considered enrolled?",
     "A student is not considered enrolled unless the minimum down payment has been paid, in addition to the other requirements for enrolment.",
     "A student is not considered enrolled unless the minimum down payment has been paid", 35),
    ("Library Hours and Facilities", "How many books can a faculty member borrow from the library?",
     "A faculty member may borrow a maximum of five (5) books for a period not exceeding one (1) month per book, which may be extended for a similar period upon presentation of the book, provided it is not being sought by someone else.",
     "A faculty may borrow a maximum of five (5) books for a period not exceeding one (1)", 86),
    ("Library Hours and Facilities", "How many library branches does the University have?",
     "The formerly single library has been divided into four separate branches: the main library in Building H, the high school library, the elementary school library, and the Graduate and Law School branch.",
     "the formerly single library has been divided into four separate branches", 86),
    ("Library Hours and Facilities", "How large is the University's book collection?",
     "The total book collection of the University is in excess of 100,000 different titles. Library opening hours are not stated in the supplied handbooks.",
     "the total book collection of the University is in excess of 100,000 different titles", 85),
    ("Student Services and Offices", "How must students wear their ID?",
     "All currently enrolled students are required to wear their ID slung over their necks at all times while inside the campus.",
     "All currently enrolled students are required to wear their ID slung over their necks at all times", 21),
    ("Student Services and Offices", "Where does a student get an Admission Slip after an absence?",
     "A student who has been absent is required to secure an Admission Slip from the Student Development Office upon request/submission of pertinent documents.",
     "A student who has been absent is required to secure an Admission Slip from the Student", 14),
    ("Academic Policies", "What does the Student Handbook say about class attendance?",
     "A student is required to attend classes regularly and punctually.",
     "is required to attend classes regularly and punctually", 13),
    ("Academic Policies", "When is a student marked tardy, and how many tardy marks equal one absence?",
     "A student who arrives in class 10 minutes after the start of the class is marked tardy, and three tardy marks are equivalent to one absence.",
     "three tardy marks shall be equivalent to one absence", 13),
    ("Academic Policies", "What happens if a student is absent for more than 20% of the classes?",
     "A student who incurs absences of more than twenty percent (20%) of the prescribed number of class or laboratory periods during the school year or term is given a failing grade and/or NC (no credit) for the course.",
     "more than twenty percent (20%) of the prescribed number", 13),
    ("Academic Policies", "When are classes automatically suspended?",
     "In-person and online classes in all grade levels are automatically canceled when Tropical Cyclone Wind Signals (TCWS) 1, 2, 3, 4, or 5 are raised by PAG ASA.",
     "are automatically canceled when Tropical Cyclone Wind Signals (TCWS) 1, 2, 3, 4, or 5 are raised by PAG ASA", 14),
    ("Faculty Policies", "How must faculty members wear their ID cards?",
     "All faculty are required to wear their Identification Cards at all times around their necks while within the school premises.",
     "All faculty will be required to wear Identification Cards (ID) cards at all times around their necks while within the school premises.", 82),
    ("Faculty Policies", "At what age do JRU employees normally retire?",
     "The normal retirement age for JRU employees is sixty (60) years old.",
     "The normal retirement age for JRU employees is sixty (60) years old.", 79),
    ("Faculty Policies", "When is a medical certificate not required for sick leave?",
     "Sick leave of three (3) days or less does not require a medical certification (see the handbook for the conditions on Fridays, Mondays, and holidays).",
     "Sick leave for three (3) days or less will not require a medical certification", 75),
    ("Faculty Policies", "Can regular faculty carry over vacation leave?",
     "No. Vacation leave/grace period is non-cumulative and non-convertible to cash.",
     "Vacation leave/grace period is non-cumulative and non-convertible to cash", 75),
    ("Faculty Policies", "What is the maximum lecture-hour absence for a faculty member in a semestral course?",
     "The maximum is three (3) lecture hours for any semestral course.",
     "is a maximum of three (3) lecture hours for any semestral course", 74),
    ("General University Information", "What is the difference between the Student Handbook and the Faculty Handbook?",
     "The Student Handbook is a guide to students' activities and behavior inside and off campus, while the Faculty Handbook informs college faculty of their duties, responsibilities, norms of conduct, and benefits.",
     "This handbook shall serve as a guide in the students' activities and behavior inside and off campus", 6),
]


def get_faqs():
    faqs = []
    for i, (cat, q, a, ev, pg) in enumerate(_ENTRIES):
        handbook, hb_page = handbook_for_page(COMBINED_PDF_NAME, pg)
        faqs.append({"id": i, "category": cat, "question": q, "answer": a, "evidence": ev,
                     "pdf_page": pg, "handbook": handbook, "page": hb_page})
    return faqs


def faqs_by_category(categories):
    faqs = get_faqs()
    return {c: [f for f in faqs if f["category"] == c] for c in categories}
