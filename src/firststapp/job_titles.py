"""Job-title suggestions for the search box.

A curated list of common titles, kept local on purpose: LinkedIn's typeahead is
not a public API, and a suggestion list that needs a network round trip per
keystroke would be both slow and another way to get rate limited.

The list is a starting point, never a restriction — the search box accepts any
text, so an unusual title is typed as normal. Titles the user has actually
searched for are offered first.
"""

from __future__ import annotations

#: Common titles across functions, deliberately region-neutral.
TITLES: tuple[str, ...] = (
    # Software engineering
    "Android Developer",
    "Backend Developer",
    "Backend Engineer",
    "C++ Developer",
    "Cloud Engineer",
    "Data Engineer",
    "Database Administrator",
    "DevOps Engineer",
    ".NET Developer",
    "Embedded Software Engineer",
    "Engineering Manager",
    "Frontend Developer",
    "Frontend Engineer",
    "Full Stack Developer",
    "Full Stack Engineer",
    "Game Developer",
    "Go Developer",
    "iOS Developer",
    "Java Developer",
    "JavaScript Developer",
    "Machine Learning Engineer",
    "Mobile Developer",
    "Node.js Developer",
    "PHP Developer",
    "Platform Engineer",
    "Python Developer",
    "QA Engineer",
    "React Developer",
    "Ruby on Rails Developer",
    "Rust Developer",
    "Salesforce Developer",
    "Security Engineer",
    "Site Reliability Engineer",
    "Software Architect",
    "Software Developer",
    "Software Engineer",
    "Solutions Architect",
    "Systems Engineer",
    "Technical Lead",
    "Test Automation Engineer",
    "Web Developer",
    "WordPress Developer",
    # Data & analytics
    "Analytics Engineer",
    "BI Developer",
    "Business Analyst",
    "Business Intelligence Analyst",
    "Data Analyst",
    "Data Architect",
    "Data Scientist",
    "Database Developer",
    "Financial Analyst",
    "Machine Learning Scientist",
    "Quantitative Analyst",
    "Research Scientist",
    "Reporting Analyst",
    "Statistician",
    # Design
    "Art Director",
    "Brand Designer",
    "Content Designer",
    "Creative Director",
    "Graphic Designer",
    "Industrial Designer",
    "Interaction Designer",
    "Motion Designer",
    "Product Designer",
    "Service Designer",
    "UI Designer",
    "UI/UX Designer",
    "User Experience Designer",
    "User Researcher",
    "UX Designer",
    "UX Researcher",
    "UX Writer",
    "Visual Designer",
    "Web Designer",
    # Product & project
    "Agile Coach",
    "Delivery Manager",
    "Product Analyst",
    "Product Manager",
    "Product Owner",
    "Program Manager",
    "Project Coordinator",
    "Project Manager",
    "Scrum Master",
    "Technical Product Manager",
    # IT & infrastructure
    "Cloud Architect",
    "Cybersecurity Analyst",
    "Help Desk Technician",
    "Information Security Analyst",
    "IT Manager",
    "IT Support Specialist",
    "Network Administrator",
    "Network Engineer",
    "Penetration Tester",
    "Systems Administrator",
    "Technical Support Engineer",
    # Marketing & content
    "Brand Manager",
    "Communications Manager",
    "Content Manager",
    "Content Strategist",
    "Content Writer",
    "Copywriter",
    "Digital Marketing Manager",
    "Digital Marketing Specialist",
    "Email Marketing Specialist",
    "Growth Marketing Manager",
    "Marketing Analyst",
    "Marketing Coordinator",
    "Marketing Manager",
    "Performance Marketing Manager",
    "Product Marketing Manager",
    "Public Relations Manager",
    "SEO Specialist",
    "Social Media Manager",
    "Technical Writer",
    # Sales, success & support
    "Account Executive",
    "Account Manager",
    "Business Development Manager",
    "Business Development Representative",
    "Customer Service Representative",
    "Customer Success Manager",
    "Customer Support Specialist",
    "Inside Sales Representative",
    "Key Account Manager",
    "Partnerships Manager",
    "Sales Development Representative",
    "Sales Engineer",
    "Sales Manager",
    "Sales Representative",
    "Solutions Consultant",
    # Finance, legal & compliance
    "Accountant",
    "Accounts Payable Specialist",
    "Auditor",
    "Bookkeeper",
    "Compliance Officer",
    "Controller",
    "Corporate Counsel",
    "Credit Analyst",
    "Finance Manager",
    "Financial Controller",
    "Investment Analyst",
    "Legal Counsel",
    "Paralegal",
    "Payroll Specialist",
    "Risk Analyst",
    "Tax Accountant",
    "Treasury Analyst",
    # People & operations
    "Executive Assistant",
    "Facilities Manager",
    "HR Business Partner",
    "HR Generalist",
    "HR Manager",
    "Learning and Development Manager",
    "Office Manager",
    "Operations Analyst",
    "Operations Manager",
    "People Operations Manager",
    "Recruiter",
    "Recruitment Consultant",
    "Talent Acquisition Specialist",
    # Supply chain & manufacturing
    "Buyer",
    "Logistics Coordinator",
    "Maintenance Technician",
    "Manufacturing Engineer",
    "Procurement Manager",
    "Production Manager",
    "Quality Assurance Manager",
    "Quality Engineer",
    "Supply Chain Analyst",
    "Supply Chain Manager",
    "Warehouse Manager",
    # Engineering (non-software)
    "Chemical Engineer",
    "Civil Engineer",
    "Electrical Engineer",
    "Environmental Engineer",
    "Mechanical Engineer",
    "Process Engineer",
    "Structural Engineer",
    # Healthcare & life sciences
    "Biomedical Scientist",
    "Clinical Research Associate",
    "Dentist",
    "Dietitian",
    "General Practitioner",
    "Healthcare Assistant",
    "Laboratory Technician",
    "Medical Doctor",
    "Nurse",
    "Occupational Therapist",
    "Pharmacist",
    "Physiotherapist",
    "Psychologist",
    "Radiographer",
    "Registered Nurse",
    "Veterinarian",
    # Education & research
    "Academic Researcher",
    "Curriculum Developer",
    "Instructional Designer",
    "Lecturer",
    "Teacher",
    "Teaching Assistant",
    "Training Specialist",
    # Leadership
    "Chief Executive Officer",
    "Chief Financial Officer",
    "Chief Marketing Officer",
    "Chief Operating Officer",
    "Chief Technology Officer",
    "Director of Engineering",
    "Director of Operations",
    "Head of Data",
    "Head of Design",
    "Head of Marketing",
    "Head of Product",
    "Managing Director",
    "Vice President of Sales",
    # Other common roles
    "Administrative Assistant",
    "Architect",
    "Barista",
    "Chef",
    "Construction Manager",
    "Consultant",
    "Data Entry Clerk",
    "Driver",
    "Electrician",
    "Event Manager",
    "Interpreter",
    "Journalist",
    "Photographer",
    "Real Estate Agent",
    "Receptionist",
    "Retail Store Manager",
    "Security Officer",
    "Social Worker",
    "Translator",
    "Travel Consultant",
    "Video Editor",
)

#: How many past searches to keep and offer at the top of the list.
MAX_RECENT = 8


def suggestions(recent: tuple[str, ...] | list[str] = (), current: str | None = None) -> list[str]:
    """Titles to offer, most recently searched first.

    ``current`` is whatever the box holds right now. It has to be part of the
    options even when it is a title the user just typed: the widget rebuilds
    its list on every rerun, and a value missing from that list is discarded —
    which silently threw away any title outside :data:`TITLES`.

    A recent search already in :data:`TITLES` is not repeated further down.
    """
    seen: set[str] = set()
    out: list[str] = []
    leading = [current] if current else []

    for title in leading + list(recent) + sorted(TITLES, key=str.lower):
        key = title.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(title.strip())

    return out


def remember(recent: tuple[str, ...] | list[str], title: str) -> tuple[str, ...]:
    """Return ``recent`` with ``title`` moved to the front, capped and deduped."""
    title = (title or "").strip()
    if not title:
        return tuple(recent)

    kept = [item for item in recent if item.strip().lower() != title.lower()]
    return tuple([title, *kept][:MAX_RECENT])
