# Main Street Coffee & Books (MSCB) — Story Bible (Canon)

*Source: MSCB Story Bible v1.1 (May 7, 2026), the working canon, minus booth-production notes. Additions since v1.1 (CNT 180 at TechServe; student-named entities) are marked* **[v1.2]**.

MSCB is the default scenario universe for every course. Use it whenever an example, case, lab, or quiz stem needs a setting. Use a different scenario only when the instructor asks. If a detail isn't in this file, keep it generic; don't invent canon.

## At a glance

| | |
|---|---|
| Business | Main Street Coffee & Books (MSCB) |
| Owners | Sarah Caldwell and James Vasquez; co-owners and longtime friends who met working at a coffee shop in Bellingham |
| Location | Commercial Avenue, downtown Anacortes, WA |
| Founded | 2017 |
| Employees | 2 owners, 4 part-time staff (2 named: Maya Chen and Ben Halvorsen) |
| Concept | Independent neighborhood coffee shop and bookstore in one space |
| IT services | Cascadia Tech Services (endpoint, help desk) and TechServe Solutions (servers, infrastructure, virtualization, cloud, automation **[v1.2]**) |
| Cloud | AWS: S3 for nightly backups, Glacier for long-term retention; second-location architecture in planning |
| Second location | Kent, WA, under active CNT 256 architectural planning (lease not yet signed) |

## People

**Sarah Caldwell** (co-owner) runs the front of the house: pulling shots, greeting regulars, chalkboard specials, training baristas, and nearly every customer conversation. She calls Cascadia when a card terminal freezes mid-rush. "Sarah called in a ticket about…" is a common CNT 160 opener.

**James Vasquez** (co-owner) runs the back: books, buying, hiring, payroll, the lease, publisher and roaster relationships. He notices when inventory numbers don't match the shelf, which is how many CNT 290 database scenarios begin. He isn't technical, but he knows what "the system is down" costs per hour and takes his service contracts seriously.

Neither owner claims to understand MSCB's IT. That's the point: *they are the users every CNT student is ultimately serving.*

**Maya Chen** is a barista on evening and weekend shifts. She's younger, fast on the espresso machine, and picks up POS quirks quickly. She's often the one who notices something "doing that weird thing again," and is the typical user in CNT 160 tickets where the issue is mild and the user is observant.

**Ben Halvorsen** is a bookseller on weekday daytime shifts. He's older, deeply knowledgeable about books, patient with customers, and slower with technology. He's the typical user in tickets where the fix must be explained without jargon, so students practice the shame-free, plain-language register.

**Unnamed staff:** two more part-timers exist, referred to as "the new barista" or "the weekend hire." Instructors may introduce ad-hoc characters this way without adding to canon.

### Student-named entities (exonyms of identity) **[v1.2]**

Some parts of MSCB are **deliberately unnamed**, and they stay that way in canon:

- a **regular customer**
- the **roaster** MSCB buys from
- a **competing coffee shop** down the street

**Students name them.** A student's name for one of these is an exonym of the student's own identity in this space. It's their mark on the MSCB world, and it belongs to them. It is not added to shared canon.

When you write materials:
- Refer to these entities generically ("a regular," "the roaster," "the shop down the street"), or leave a slot the student fills in, e.g. `[your regular's name]`.
- **Never supply a name** for them, even as an example, and never carry one student's name into another student's materials.
- Inside one student's own work, use the name that student gave, as they gave it.

## The store and the town

MSCB occupies a restored single-story brick-fronted building on Commercial Avenue that was earlier a hardware store, a stationer, and a video rental. The interior is split roughly into thirds:
- a coffee bar and pastry case at the front
- bookshelves and reading nooks in the middle
- back of house: office, IT closet, stockroom, and an alley door

Anacortes is a working port town on Fidalgo Island and the ferry terminal to the San Juans, with about 17,000 people. **Seasonality matters.** Winter brings mostly regulars and slower mornings, and James orders heavier reads. Summer brings ferry foot traffic, lots of paperbacks, and much higher espresso volume. A POS outage on a Saturday in July is not the same problem as one on a Tuesday in February.

## The business structure in hardware

Every business decision shows up as hardware, and each layer is owned and touched by a different entity. *Follow the hardware and you've followed the business.*

### Layer 1 — Front of house (MSCB owns; MSCB and Cascadia touch) → CNT 160 world
- 2 × POS terminals (espresso station, register): touchscreen all-in-ones, thin-client style, browser-based POS UI talking to the back-end database
- 1 × receipt printer, networked to both terminals
- 1 × card reader per terminal, on the PCI-isolated segment, talking to the payment processor
- 1 × tablet James uses on the floor for special-order lookups and mobile inventory

### Layer 2 — Back of house (MSCB owns; Cascadia touches)
- **CLIENT01**: Windows 11 workstation joined to the AD domain; James uses it for ordering, accounting, scheduling, reporting
- 1 × multifunction printer/scanner (invoices, purchase orders)
- 1 × extra monitor (Sarah's shift schedules)

### Layer 3 — IT closet (MSCB owns the room and gear; TechServe touches the network gear)
- ISP cable modem (ISP-provided)
- pfSense firewall (Netgate-class) with VLANs: PCI segment, staff network, management network, guest WiFi
- 24-port managed switch with VLAN support and PoE for the APs
- 2 × WiFi access points (front, back)
- UPS (APC SmartUPS-class, ~1500VA)
- Patch panel for front-of-house and back-office runs

**MSCB does not host its own servers.** That decision, made in 2022 when TechServe came on board, is the pivot that defines MSCB's IT story.

### Layer 4 — Off-site at TechServe (TechServe owns and operates) → CNT 290 world
MSCB's production VMs run as tenant VMs on TechServe's **bknown / bknown2 Proxmox cluster**:
- **DC01**: Windows Server 2022. It runs AD, DNS, DHCP and file shares, plus two MariaDB instances:
  - `mscb` on port **3306** (inventory, customer relationships, ordering)
  - `pos_db` on port **3307** (POS transactions)
  - A federated link keeps inventory in sync after each sale.
- **CLIENT01-image**: golden image for rebuilding the back-office workstation
- **Linux utility VM**: backups, scheduled jobs, and the cron that ships data to AWS

### Layer 5 — AWS (MSCB pays AWS; TechServe architects) → CNT 256 world
- **S3**: nightly encrypted backups of `mscb` and `pos_db` at 02:00 from the utility VM. The bucket has encryption, versioning, and MFA delete on the production bucket.
- **Lifecycle policy**: current versions stay in S3 Standard for 30 days, then Standard-IA for 60 days, then Glacier Flexible Retrieval. Old versions expire after one year.
- **IAM user**: the backup job can write to the backup bucket and nothing else.
- **AWS Backup vault**: under evaluation, separate from the application-level dumps.
- **Kent expansion design**: VPC, hybrid identity, RDS or hosted MariaDB, multi-site replication, Route 53, cost model.

## The Kent expansion

Sarah and James are evaluating a second location in **Kent, WA**, for four reasons:
- **Market:** a large, growing residential and commercial base, underserved by independent coffee-and-books shops.
- **Distance:** far enough to be a real branch with its own staff, POS and network, but close enough to drive to.
- **Connectivity:** fiber availability that Anacortes doesn't always have.
- **Local stakes:** Kent is next to Renton, so the students are architecting infrastructure in their own backyard.

Kent will not host servers either. The CNT 256 question: *extend TechServe's on-prem stack to Kent over a VPN, or lift MSCB's production into AWS and serve both stores from there?* Both answers are defensible. That tension is the lab.

## The steps of a transaction

This is the canonical reference for any lab or item that touches the transaction path. Maya rings up a 12oz Sumatra and a paperback at the front register:

| # | What Maya sees | What's actually happening | Layer | Course |
|---|---|---|---|---|
| 1 | Unlocks the POS at 6:30 AM | Her account authenticates against AD on DC01 (offsite at TechServe) over the VPN tunnel | 4 | CNT 290 (AD, identity) |
| 2 | Rings up the items | Browser-based POS UI sends the cart to the POS application backend | 1 → 4 | CNT 290 (app server, networking) |
| 3 | Customer taps card | Card reader sends the auth request through the PCI VLAN, out through pfSense, to the payment processor | 3 | CNT 160 (terminal, security awareness) + CNT 290 (firewall, segmentation) |
| 4 | "Approved" | Processor returns approval; POS commits the sale | Cross-layer | All |
| 5 | Receipt prints | Transaction written to `pos_db` (DC01:3307) | 4 | CNT 290 (database) |
| 6 | (invisible) | Trigger on `pos_db` fires; federated link to `mscb` (DC01:3306) decrements inventory | 4 | CNT 290 (federated tables, replication) |
| 7 | (invisible) | Transaction appears in James's 8:30 AM morning report query the next day | 4 → 2 | CNT 290 (reporting) + CNT 180 (report script) **[v1.2]** |
| 8 | (invisible) | At 02:00 the utility VM runs `mysqldump` of both databases, then gzips, encrypts and uploads them to S3 | 4 → 5 | CNT 256 (S3, IAM, backup architecture) + CNT 180 (the backup job's code) **[v1.2]** |
| 9 | (30+ days later) | Lifecycle moves the backup Standard → Standard-IA (day 30) → Glacier (day 90); old versions expire after one year | 5 | CNT 256 (lifecycle, cost) |

*One tap of a card, nine steps, three CNT courses, layers in three physical locations, and four named people whose livelihoods depend on the whole chain working.*

## How MSCB got here

- **2017, opening:** iPad POS, free email, a personal printer, and a shared Google Sheet for inventory.
- **2019, first scaling pain:** holiday online preorders break the Sheet, so a freelancer builds a basic inventory app.
- **2020, COVID:** curbside pickup, online ordering and e-commerce arrive. The freelancer is overwhelmed and systems break in ways no one understands.
- **2021, Cascadia Tech Services arrives** after a Saturday register failure. They stabilize the desktops and take over help-desk tickets.
- **2022, TechServe Solutions joins:** Cascadia refers them, and TechServe proposes the pivot: *don't put servers in the coffee shop.* Production VMs move to TechServe's Proxmox cluster, and the closet shrinks to network gear.
- **2023, stabilization:** AD, MariaDB POS on DC01:3307, the federated link to inventory on DC01:3306, file services and scheduled jobs.
- **2024, cloud begins:** the S3 backup pipeline, lifecycle policies, and Glacier.
- **2025:** second-location conversations begin.
- **2026 (now):** Kent is architecturally live; the lease is not signed.

## The service firms (also the students' employers)

**Cascadia Tech Services** is the employer for **CNT 160 (A+ Core 2)**:
- Students are junior support technicians on the help-desk rotation.
- The work is reactive, ticket-driven, customer-facing and endpoint-focused: printers, account lockouts, malware suspicions, software installs, patching.
- They talk directly with Sarah, Maya, Ben and other staff.
- The voice is friendly and plain. Larger architectural issues get escalated rather than touched.

**TechServe Solutions** is the employer for **CNT 290 (Proxmox / Data Center Virtualization)**, **CNT 256 (AWS SAA)**, and **CNT 180 (Python) [v1.2]**:
- CNT 290 and 256 students are junior infrastructure admins. CNT 180 students are junior automation developers who write and maintain the Python on the utility VM: scheduled jobs, reports, and data checks. **[v1.2]**
- The work is project-based, change-controlled, server-side, and mostly invisible to MSCB staff.
- They talk to Sarah and James only when impact reaches the business ("down for ten minutes Tuesday at 6 AM").
- The voice is documentation-heavy and precise.

The firms work together. Cascadia escalates server-side issues to TechServe, TechServe loops Cascadia in when server changes affect endpoints, and neither poaches the other's contracts. *This is the model for how the courses' students should think about each other professionally.*

## Pain points by course

**CNT 160 (Cascadia):** Every one of these is a real ticket that maps to a 220-1202 objective.
- Sarah's POS terminal shows a strange certificate warning.
- Maya can't print receipts.
- Ben's account locked itself out and he doesn't know why.
- CLIENT01 is running slowly, and James thinks he may have clicked something he shouldn't have.
- A new barista needs an account and security-basics training.

**CNT 290 (TechServe):** Every one of these is a real project in the data center virtualization curriculum.
- A snapshot strategy is needed before a risky Proxmox upgrade.
- MariaDB POS replication is needed so a Saturday outage doesn't kill the day.
- A federated query is timing out, and James's morning report is missing inventory.
- The AD forest needs a new OU structure as MSCB grows.
- The pfSense rules need an audit.

**CNT 180 (TechServe) [v1.2]:** Every one of these is real automation work on the utility VM.
- The 02:00 backup job is a fragile shell script; it needs to be rewritten in Python, with logging and a clear failure alert.
- James's 8:30 AM morning report is a query he runs by hand; it needs to become a script that produces a readable file every morning.
- The shelf count and `mscb` inventory don't match; a reconciliation script should list the differences instead of James hunting for them.
- Sarah wants to know how July Saturdays differ from February Tuesdays; POS sales data needs parsing and summarizing.
- A new barista's account request arrives as an email; a small script could validate it before it becomes a Cascadia ticket.

**CNT 256 (TechServe):** Every one of these is a real architecture decision that maps to SAA-C03 domains.
- How does identity extend to Kent?
- Where does the database live?
- Should production lift into AWS, or should the on-prem stack extend to Kent?
- What's the disaster recovery story?
- What does it cost per month, and which levers cut the bill in half?

A student who takes all four courses works the same business in four professional roles.

## Canon rules (don't change)

1. The business is **Main Street Coffee & Books**, abbreviated **MSCB**. Use the name, not "the customer" or "the client."
2. The owners are **Sarah Caldwell** and **James Vasquez**, co-owners and longtime friends.
3. The location is **Anacortes, WA**, on **Commercial Avenue**.
4. Recurring staff are **Maya Chen** (barista) and **Ben Halvorsen** (bookseller).
5. The firms are **Cascadia Tech Services** (CNT 160) and **TechServe Solutions** (CNT 290 / CNT 256 / CNT 180). Don't mix them within a course.
6. **MSCB does not host its own servers.** Production lives at TechServe; backups live in AWS S3.
7. The second-location target is **Kent, WA**.
8. **The student is always the active agent.** Sarah, James, Maya, and Ben are recurring NPCs, never the protagonist: they report, ask, and decide business questions, while the student diagnoses and fixes.
9. Pocket Pedagogy framing applies: shame-free language, why before how, scenario-anchored, honor existing knowledge.
10. Technical complexity scales with the course, not the scenario. The same MSCB story can host a CNT 160 printer ticket and a CNT 290 replication build.
11. **[v1.2]** The regular customer, the roaster, and the competing shop are **named by students, never by canon or by Emile**. A student's name for them is an exonym of that student's identity in MSCB.

## Still open

- Nothing blocking. A newer bible replaces this file when one exists.
