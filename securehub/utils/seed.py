from models import db
from models.user import User
from models.department import Department
from models.order import Order
from models.document import Document
from models.ticket import Ticket
from models.report import Report
from models.notification import Notification

def seed_database():
    db.create_all()

    # Define Department specs
    dept_specs = {
        "IT": "Information Technology and core infrastructure.",
        "Finance": "Financial auditing, accounting, and budget control.",
        "HR": "Human resources, personnel, and compliance onboarding.",
        "Sales": "Sales, client relations, and procurement logistics.",
        "Operations": "Security operations, monitoring, and facility management."
    }

    depts = {}
    for d_name, d_desc in dept_specs.items():
        dept = Department.query.filter_by(name=d_name).first()
        if not dept:
            # Fallback check for existing legacy department names
            if d_name == "IT":
                dept = Department.query.filter(Department.name.like("%Information Technology%")).first()
            elif d_name == "Sales":
                dept = Department.query.filter(Department.name.like("%Sales%")).first()
            elif d_name == "Operations":
                dept = Department.query.filter(Department.name.like("%Security%")).first()

        if not dept:
            dept = Department(name=d_name, description=d_desc)
            db.session.add(dept)
            db.session.commit()
        else:
            dept.name = d_name
            dept.description = d_desc
            db.session.commit()
        depts[d_name] = dept

    # User Specs (Exactly 10 users as specified)
    user_specs = [
        {"username": "alice",   "password": "alice123",   "role": "User",    "dept": "IT",         "email": "alice@securehub.internal"},
        {"username": "bob",     "password": "bob123",     "role": "Manager", "dept": "Finance",    "email": "bob@securehub.internal"},
        {"username": "admin",   "password": "admin123",   "role": "Admin",   "dept": "IT",         "email": "admin@securehub.internal"},
        {"username": "charlie", "password": "charlie123", "role": "User",    "dept": "HR",         "email": "charlie@securehub.internal"},
        {"username": "david",   "password": "david123",   "role": "User",    "dept": "Sales",      "email": "david@securehub.internal"},
        {"username": "emma",    "password": "emma123",    "role": "Manager", "dept": "HR",         "email": "emma@securehub.internal"},
        {"username": "frank",   "password": "frank123",   "role": "User",    "dept": "Finance",    "email": "frank@securehub.internal"},
        {"username": "grace",   "password": "grace123",   "role": "User",    "dept": "Sales",      "email": "grace@securehub.internal"},
        {"username": "henry",   "password": "henry123",   "role": "Manager", "dept": "IT",         "email": "henry@securehub.internal"},
        {"username": "isla",    "password": "isla123",    "role": "User",    "dept": "Operations", "email": "isla@securehub.internal"}
    ]

    users = {}
    for spec in user_specs:
        u = User.query.filter_by(username=spec["username"]).first()
        dept_obj = depts[spec["dept"]]
        if not u:
            u = User(
                username=spec["username"],
                email=spec["email"],
                role=spec["role"],
                department_id=dept_obj.id
            )
            u.set_password(spec["password"])
            db.session.add(u)
            db.session.commit()
        else:
            u.role = spec["role"]
            u.department_id = dept_obj.id
            u.email = spec["email"]
            if not u.check_password(spec["password"]):
                u.set_password(spec["password"])
            db.session.commit()
        users[spec["username"]] = u

    # Create Orders for users if not existing
    orders_data = [
        {"user": "alice",   "dept": "IT",         "num": "ORD-2026-001", "desc": "HSM Security Key Tokens", "status": "Completed"},
        {"user": "bob",     "dept": "Finance",    "num": "ORD-2026-002", "desc": "Financial Ledger Audit Server", "status": "Approved"},
        {"user": "charlie", "dept": "HR",         "num": "ORD-2026-003", "desc": "HR Onboarding Workstations x5", "status": "Pending"},
        {"user": "admin",   "dept": "IT",         "num": "ORD-2026-004", "desc": "Core Firewall Appliance Backup", "status": "Shipped"},
        {"user": "david",   "dept": "Sales",      "num": "ORD-2026-005", "desc": "Client CRM Terminal Upgrades", "status": "Pending"},
        {"user": "emma",    "dept": "HR",         "num": "ORD-2026-006", "desc": "Payroll Encryption Module License", "status": "Approved"},
        {"user": "frank",   "dept": "Finance",    "num": "ORD-2026-007", "desc": "Tax Filing Database Backup Drive", "status": "Completed"},
        {"user": "grace",   "dept": "Sales",      "num": "ORD-2026-008", "desc": "Field Sales Tablet Devices x8", "status": "Pending"},
        {"user": "henry",   "dept": "IT",         "num": "ORD-2026-009", "desc": "Enterprise Switch Refresh Kit", "status": "Approved"},
        {"user": "isla",    "dept": "Operations", "num": "ORD-2026-010", "desc": "SOC Monitoring Wall Monitors", "status": "Pending"}
    ]

    for o_spec in orders_data:
        if not Order.query.filter_by(order_number=o_spec["num"]).first():
            u_obj = users[o_spec["user"]]
            d_obj = depts[o_spec["dept"]]
            ord_item = Order(
                user_id=u_obj.id,
                department_id=d_obj.id,
                order_number=o_spec["num"],
                description=o_spec["desc"],
                status=o_spec["status"]
            )
            db.session.add(ord_item)
    db.session.commit()

    # Create Documents for users
    docs_data = [
        {"owner": "alice",   "title": "Alice's Incident Response Plan", "desc": "Confidential IR procedure for Tier 1 analysts.", "content": "Classification: RESTRICTED\n\nSteps for initial containment of endpoint intrusions..."},
        {"owner": "bob",     "title": "Q3 Financial Audit Strategy", "desc": "Managerial overview of quarterly accounting security.", "content": "Classification: CONFIDENTIAL\n\nFinancial ledger encryption standards and audit trail policies..."},
        {"owner": "admin",   "title": "Enterprise Key Management Audit", "desc": "Root CA & Vault master key ceremony logs.", "content": "Classification: TOP SECRET\n\nRoot key custodians list and HSM backup verification hashes..."},
        {"owner": "david",   "title": "Sales Client Data Security Standards", "desc": "Guidance on handling client NDA materials.", "content": "Classification: INTERNAL\n\nStandard protocol for storing customer PII in cloud databases..."},
        {"owner": "emma",    "title": "HR Employee Offboarding Security", "desc": "Revocation matrix for departed personnel.", "content": "Classification: RESTRICTED\n\nImmediate checklist for deactivating active Directory credentials..."},
        {"owner": "frank",   "title": "Tax Regulation Compliance Summary", "desc": "Overview of state and federal tax data requirements.", "content": "Classification: INTERNAL\n\nVerification steps for encrypted tax archive storage..."},
        {"owner": "grace",   "title": "Regional Sales Contract NDA Template", "desc": "Standard agreement form for vendor partners.", "content": "Classification: PUBLIC\n\nTemplate terms for mutual non-disclosure of pricing tier structures..."},
        {"owner": "henry",   "title": "IT Network Infrastructure Map", "desc": "VLAN subnet layout and edge firewall rules.", "content": "Classification: CONFIDENTIAL\n\nDiagram of core switches, DMZ hosts, and internal jump boxes..."},
        {"owner": "isla",    "title": "Operations Physical Access Log", "desc": "Facility badge swipe records for datacenter floor.", "content": "Classification: RESTRICTED\n\nDaily log of visitor access passes and biometric verification..."}
    ]

    for d_spec in docs_data:
        u_obj = users[d_spec["owner"]]
        if not Document.query.filter_by(owner_id=u_obj.id, title=d_spec["title"]).first():
            doc_item = Document(
                owner_id=u_obj.id,
                title=d_spec["title"],
                description=d_spec["desc"],
                content=d_spec["content"]
            )
            db.session.add(doc_item)
    db.session.commit()

    # Create Tickets
    tickets_data = [
        {"creator": "alice",   "assignee": "henry", "title": "VPN Access Request for Contractor", "desc": "Need temporary VPN credentials configured for audit team.", "status": "In Progress", "priority": "High"},
        {"creator": "charlie", "assignee": "admin", "title": "HR Portal Password Reset Issue", "desc": "Locked out of CRM portal after multiple failed attempts.", "status": "Open", "priority": "Medium"},
        {"creator": "bob",     "assignee": "admin", "title": "Upgrade Financial Database Firmware", "desc": "Patch critical CVE-2026-9901 vulnerability on edge database router.", "status": "Resolved", "priority": "Critical"},
        {"creator": "david",   "assignee": "henry", "title": "Sales Laptop Wi-Fi Certificate Expired", "desc": "Cannot connect to internal enterprise wireless SSID.", "status": "Open", "priority": "High"},
        {"creator": "frank",   "assignee": "emma",  "title": "Finance User Access Review", "desc": "Requesting annual access validation report for quarterly audit.", "status": "In Progress", "priority": "Low"},
        {"creator": "isla",    "assignee": "henry", "title": "Datacenter Air Handler Alarm", "desc": "Secondary HVAC unit reporting temperature spike in Rack B4.", "status": "Open", "priority": "Critical"}
    ]

    for t_spec in tickets_data:
        creator_obj = users[t_spec["creator"]]
        assignee_obj = users[t_spec["assignee"]] if t_spec["assignee"] else None
        if not Ticket.query.filter_by(created_by=creator_obj.id, title=t_spec["title"]).first():
            ticket_item = Ticket(
                created_by=creator_obj.id,
                assigned_to=assignee_obj.id if assignee_obj else None,
                title=t_spec["title"],
                description=t_spec["desc"],
                status=t_spec["status"],
                priority=t_spec["priority"]
            )
            db.session.add(ticket_item)
    db.session.commit()

    # Create Reports
    reports_data = [
        {"creator": "bob",   "title": "Monthly Financial Risk Assessment", "desc": "Scan report covering accounting databases and export nodes.", "status": "Published"},
        {"creator": "alice", "title": "Phishing Simulation Campaign Results", "desc": "Q3 employee security awareness training click-through stats.", "status": "Draft"},
        {"creator": "admin", "title": "Annual SOC 2 Type II Compliance Audit", "desc": "Auditor findings and security control efficacy summary.", "status": "Published"},
        {"creator": "emma",  "title": "HR Privacy & GDPR Audit Report", "desc": "Evaluation of employee personal record retention policies.", "status": "Published"},
        {"creator": "henry", "title": "IT Perimeter Vulnerability Assessment", "desc": "External port scan and penetration testing summary.", "status": "Published"}
    ]

    for r_spec in reports_data:
        creator_obj = users[r_spec["creator"]]
        if not Report.query.filter_by(created_by=creator_obj.id, title=r_spec["title"]).first():
            report_item = Report(
                created_by=creator_obj.id,
                title=r_spec["title"],
                description=r_spec["desc"],
                status=r_spec["status"]
            )
            db.session.add(report_item)
    db.session.commit()

    # Create Notifications
    notifs_data = [
        {"user": "alice",   "msg": "Ticket #1 'VPN Access Request' assigned to Henry.", "read": False},
        {"user": "alice",   "msg": "Welcome to SECUREHUB Enterprise Portal!", "read": True},
        {"user": "bob",     "msg": "Financial risk assessment report published successfully.", "read": False},
        {"user": "charlie", "msg": "Your password reset ticket #2 is currently Open.", "read": False},
        {"user": "david",   "msg": "Your procurement order ORD-2026-005 is Pending approval.", "read": False},
        {"user": "emma",    "msg": "New user access review ticket assigned from Frank.", "read": False},
        {"user": "frank",   "msg": "Tax database backup order ORD-2026-007 has completed.", "read": True},
        {"user": "grace",   "msg": "Welcome to SECUREHUB Sales Operations team!", "read": True},
        {"user": "henry",   "msg": "High priority ticket assigned: Datacenter Air Handler Alarm.", "read": False},
        {"user": "isla",    "msg": "SOC Monitoring Wall Monitors order placed.", "read": False}
    ]

    for n_spec in notifs_data:
        u_obj = users[n_spec["user"]]
        if not Notification.query.filter_by(user_id=u_obj.id, message=n_spec["msg"]).first():
            n_item = Notification(
                user_id=u_obj.id,
                message=n_spec["msg"],
                is_read=n_spec["read"]
            )
            db.session.add(n_item)
    db.session.commit()

    print("Database successfully seeded with 10 demo users and sample data!")
