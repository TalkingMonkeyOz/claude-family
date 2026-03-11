---
projects:
  - Project-Metis
tags:
  - project/Project-Metis
  - type/research
  - topic/library-science
  - topic/knowledge-management
created: 2026-03-10
updated: 2026-03-10
status: active
---

# Library Science Cataloging and Retrieval Systems — Research for METIS

## Purpose

This document surveys the major classification systems, cataloging standards, retrieval mechanisms, collection management strategies, and digital library practices from the field of Library and Information Science (LIS). Each section concludes with observations on how these concepts translate to AI knowledge management, specifically the METIS system being designed for multi-project, multi-agent coordination.

---

## 1. Classification Systems

Classification is the act of organizing knowledge into categories so that items on similar subjects are grouped together and can be located predictably. Library classification systems have evolved from simple enumerative lists (pre-built classes for every possible topic) toward faceted and analytico-synthetic approaches (composing class numbers from independent facets at cataloging time). Understanding these systems illuminates different strategies for organizing an AI's knowledge base.

### 1.1 Dewey Decimal Classification (DDC)

**Origin**: Melvil Dewey, 1876. Now in its 23rd edition, maintained by OCLC.

**Structure**: Hierarchical, purely numeric notation. Ten main classes (000-999), each subdivided into ten divisions, each further into ten sections, with decimal extension for arbitrary specificity.

| Class | Subject |
|-------|---------|
| 000 | Computer Science, Information, General Works |
| 100 | Philosophy and Psychology |
| 200 | Religion |
| 300 | Social Sciences |
| 400 | Language |
| 500 | Natural Sciences and Mathematics |
| 600 | Technology (Applied Sciences) |
| 700 | Arts and Recreation |
| 800 | Literature |
| 900 | History, Geography, Biography |

**Key innovations**:

- **Relative location**: Books are shelved relative to other books on similar topics, not in fixed shelf positions. This means the system adapts when new material is added without requiring reorganization of the entire collection.
- **Relative Index**: An alphabetical index that maps natural-language terms to class numbers, bridging the gap between how users think about topics and where the system places them.
- **Number building**: When no pre-assigned number exists for a specific topic, classifiers can synthesize numbers by combining elements from the main schedules with auxiliary tables (Standard Subdivisions, geographic areas, languages, ethnic groups, etc.). This provides extensibility without requiring every possible combination to be enumerated in advance.

**Handling cross-cutting topics**: DDC's strictly hierarchical structure creates a fundamental problem: a book on "the economics of religion" must go in either 200 (Religion) or 300 (Social Sciences), not both. DDC addresses this through:

- **Interdisciplinary numbers**: Some numbers are designated as collecting points for topics that span disciplines.
- **Class-elsewhere notes**: Instructions directing the classifier to related numbers in other parts of the schedule.
- **Add instructions**: Rules for appending notation from one part of the schedule to another.
- **Multiple access points**: While the book sits in one physical location, catalog records can provide subject access under multiple headings.

**Limitations**: The ten-class structure reflects late 19th-century Western knowledge organization. Some disciplines are cramped (all of computer science shares 000 with general encyclopedias), while others receive disproportionate space (200 is almost entirely devoted to Christianity, with other world religions squeezed into 290-299). The system's Anglo-American bias has been a persistent criticism.

### 1.2 Library of Congress Classification (LCC)

**Origin**: Developed starting in 1897 by Herbert Putnam and Charles Martel for the Library of Congress collection. Maintained by the Library of Congress.

**Structure**: Alphanumeric notation. 21 main classes designated by single letters (I, O, W, X, Y are reserved for future use or local adaptation), with subclasses using two-letter combinations. Numbers follow for further subdivision, and Cutter numbers (alphanumeric codes representing author or topic) provide final specificity.

| Letter | Subject |
|--------|---------|
| A | General Works |
| B | Philosophy, Psychology, Religion |
| C-D | History (General, Old World) |
| E-F | History (Americas) |
| G | Geography, Anthropology, Recreation |
| H | Social Sciences |
| J | Political Science |
| K | Law |
| L | Education |
| M | Music |
| N | Fine Arts |
| P | Language and Literature |
| Q | Science |
| R | Medicine |
| S | Agriculture |
| T | Technology |
| U | Military Science |
| V | Naval Science |
| Z | Bibliography, Library Science |

**How it differs from DDC**:

- **Broader notation space**: The alphanumeric system allows far more classes without deep nesting. DDC must use long decimal strings for specificity; LCC achieves equivalent specificity with shorter call numbers.
- **Enumerative rather than synthetic**: LCC tends to enumerate specific combinations rather than providing rules for building numbers. This makes it less systematic but more practical for large research collections.
- **Literary warrant**: LCC was designed around the Library of Congress's actual collection. Classes were created and subdivided based on what books actually existed, not on a theoretical map of knowledge. This is a fundamentally different design philosophy from DDC's attempt to map all of knowledge a priori.
- **Distributed maintenance**: Each class is maintained by subject specialists at the Library of Congress, allowing deep expertise but sometimes inconsistent principles across classes.
- **No relative index**: Unlike DDC, LCC has no single comprehensive index. Each class has its own index, and cross-class navigation relies on cataloger knowledge.

**Scale**: LCC is used by most academic and research libraries in the United States. It handles the granularity needed for collections of millions of items better than DDC, which was designed for smaller public library collections.

### 1.3 Universal Decimal Classification (UDC)

**Origin**: Paul Otlet and Henri La Fontaine, 1905. Based on DDC's 5th edition but extended dramatically. Maintained by the UDC Consortium.

**Structure**: Retains DDC's ten main classes and numeric base, but adds an extensive system of auxiliary tables and connecting symbols that transform it from a purely enumerative scheme into an analytico-synthetic one.

**What makes UDC different from DDC**:

UDC's defining feature is its **auxiliary tables** — standardized facets that can be combined with any main class number:

| Auxiliary | Symbol | Purpose | Example |
|-----------|--------|---------|---------|
| Language | =... | Language of the document | =111 (English) |
| Form | (0...) | Physical form or presentation | (042) (lecture) |
| Place | (1/9) | Geographic location | (73) (USA) |
| Ethnic grouping | (=...) | Peoples and nationalities | (=414) (Celtic peoples) |
| Time | "..." | Chronological period | "19" (20th century) |
| Properties | -02 | General characteristics | Properties of materials |
| Materials | -03 | What something is made of | -036 (textile materials) |
| Persons | -05 | Persons as agents or subjects | -055.2 (women) |
| Relations | :: | Topic relationship | 17::7 (ethics in relation to art) |

**Connecting symbols** allow complex compound subjects:

- `+` (addition): joining two distinct subjects — `59+636` (zoology and animal husbandry)
- `/` (consecutive extension): spanning a range — `592/599` (systematic zoology)
- `:` (relation): connecting related topics — `77:528` (photography and surveying)
- `::` (order-fixing relation): permanent binding of concepts

This means UDC can express compound and relational subjects that DDC cannot represent in a single class number. A document about "English-language lectures on 20th-century American ethics" can be fully expressed in one UDC number by chaining the main class with relevant auxiliaries.

**Usage**: UDC is more widely used in Europe and in specialized/technical libraries. It is the most used classification system worldwide by number of countries, though DDC dominates in English-speaking public libraries.

### 1.4 Colon Classification (Ranganathan)

**Origin**: S.R. Ranganathan, 1933. The first fully faceted classification system.

**Core idea**: Rather than enumerating all possible subjects, Ranganathan proposed that any subject can be analyzed into a combination of five fundamental categories (facets), which he called **PMEST**:

| Facet | Symbol | Question | Example |
|-------|--------|----------|---------|
| **Personality** (P) | `,` (comma) | What is the main entity or thing? | Medicine, Literature, Agriculture |
| **Matter** (M) | `;` (semicolon) | What material, property, or substance is involved? | Treatment methods, cotton, steel |
| **Energy** (E) | `:` (colon) | What action, process, or operation? | Research, teaching, surgery |
| **Space** (S) | `.` (period) | Where? Geographic or spatial context | India, rural areas, tropics |
| **Time** (T) | `'` (apostrophe) | When? Chronological period | 1990s, medieval, 21st century |

**How it works**: The classifier identifies the main class of the document, then analyzes the specific subject into its constituent facets, and constructs a class number by chaining the facet values together in PMEST order, separated by the designated punctuation marks (hence "Colon" Classification — the colon being one of the separator symbols).

**Example**: "Research on malaria treatment in rural India during the 1990s"
- Main class: L (Medicine)
- Personality: Malaria
- Matter: Treatment methods
- Energy: Research
- Space: India, rural
- Time: 1990s

The class number is synthesized from these components rather than looked up in a pre-built table.

**Significance for knowledge organization**: Ranganathan's facet analysis was revolutionary because it recognized that knowledge is inherently multi-dimensional. Any document can be characterized along multiple independent axes, and the classification system should reflect this rather than forcing a single hierarchical placement. This insight directly influenced all subsequent faceted classification work and is the intellectual ancestor of modern faceted search interfaces.

**Ranganathan's canons**: Beyond PMEST, Ranganathan developed extensive theoretical apparatus including canons for the helpful sequence of foci within each facet, principles for citation order (which facet should come first in the notation), and rules for hospitality (how to accommodate new topics without restructuring existing numbers).

### 1.5 Bliss Bibliographic Classification (BC2)

**Origin**: Henry Evelyn Bliss, first edition 1940-1953. The second edition (BC2), a complete redesign, has been under development since 1977 by the Bliss Classification Association and the UK Classification Research Group (CRG).

**What makes BC2 distinctive**: BC2 is considered the most theoretically sophisticated fully faceted classification scheme in active use. It builds on Ranganathan's work but extends his five PMEST categories to **thirteen fundamental categories**, providing finer-grained facet analysis:

The thirteen categories (which vary in application across classes) include: Thing/Entity, Kind, Part, Property, Material, Process, Operation, Agent, Patient, Product, By-product, Space, and Time.

**Key features**:

- **Fully faceted within each class**: Every main class and subclass is rigorously analyzed into facets. Vocabulary within each class is organized into clearly defined, easily understood categories.
- **Brevity of notation**: Despite its theoretical sophistication, BC2 produces notations that are exceptionally brief relative to their specificity. This is achieved through careful organization that avoids redundancy.
- **Alternative locations**: BC2 provides structured guidance for alternative placements, acknowledging that different libraries may have different priorities for the same topic.
- **Bibliographic warrant and educational consensus**: Classes are structured based on both the existing literature and the consensus view of how a discipline is organized, combining pragmatism with theoretical coherence.

**Adoption**: BC2 is used primarily in UK academic libraries. It has been described as "technically much superior to other schemes" but has not achieved the market dominance of DDC or LCC, partly because those systems benefit from massive institutional inertia and tooling support.

### Classification Systems — Implications for AI Knowledge Management

| Library Concept | METIS Application |
|-----------------|-------------------|
| Hierarchical classification (DDC/LCC) | Project/domain/topic hierarchy for knowledge items. Useful as a primary organizing axis but insufficient alone. |
| Faceted classification (Ranganathan/BC2) | Every knowledge item described along multiple independent dimensions: project, domain, type, confidence, recency, source. Query by any combination. |
| Number building / synthesis | Composing retrieval queries from independent facets at query time rather than pre-assigning items to fixed categories. |
| Literary warrant | Build classification categories based on knowledge that actually exists, not theoretical completeness. Add categories when real content demands them. |
| Relative location | Knowledge items positioned relative to related items via embeddings and semantic similarity, not fixed addresses. |
| Cross-cutting topics | A single knowledge item tagged with multiple facets rather than forced into one category. Faceted retrieval handles multi-dimensional access naturally. |

---

## 2. Cataloging Standards and Metadata

Cataloging is the process of creating structured descriptions of information resources so they can be found, identified, selected, and obtained. While classification determines *where* an item goes, cataloging determines *what we say about it*.

### 2.1 MARC Records (Machine-Readable Cataloging)

**Origin**: Developed by Henriette Avram at the Library of Congress in the 1960s. MARC 21 (the current standard) resulted from the harmonization of USMARC and CAN/MARC in 1999.

**Purpose**: MARC provides a standardized digital format for representing bibliographic information so that catalog records can be shared between library systems. Before MARC, every library created its own catalog cards from scratch.

**Record structure**: A MARC record has three components:

1. **Leader** (24 characters): Fixed-length field containing metadata about the record itself — record length, status, type of resource, encoding level.

2. **Directory**: An index of all variable fields in the record, listing each field's tag, length, and starting position.

3. **Variable fields**: The actual bibliographic data, in two categories:
   - **Control fields (001-009)**: Fixed-length coded data. No indicators or subfields. Field 001 is the control number; field 008 contains 40 character positions of coded information (publication date, country, language, form, etc.).
   - **Data fields (010-999)**: Variable-length fields containing descriptive information, each identified by a three-digit tag. Data fields have two single-character **indicators** that provide additional context, and are subdivided into **subfields** marked by delimiter codes.

**Key field ranges**:

| Tag Range | Content |
|-----------|---------|
| 0XX | Control information, identifiers |
| 1XX | Main entry (author, corporate body) |
| 2XX | Title, edition, imprint (publisher, date) |
| 3XX | Physical description |
| 4XX | Series statements |
| 5XX | Notes |
| 6XX | Subject access (subject headings, classification numbers) |
| 7XX | Added entries (co-authors, related works) |
| 8XX | Series added entries, holdings |
| 9XX | Local use |

**Example subfield structure** (field 245, Title Statement):
```
245 10 $a The art of computer programming / $c Donald E. Knuth.
```
- `245` = Title Statement tag
- `1` = First indicator (title added entry: yes)
- `0` = Second indicator (nonfiling characters: 0)
- `$a` = Title subfield
- `$c` = Statement of responsibility subfield

**Legacy and future**: MARC has been remarkably durable — over 60 years in use. However, its fixed-field structure and library-specific semantics make it poorly suited for the web. BIBFRAME (Bibliographic Framework Initiative) is being developed by the Library of Congress as a linked-data replacement, modeling bibliographic data as RDF triples rather than fixed records.

### 2.2 Dublin Core

**Origin**: 1995, OCLC/NCSA workshop in Dublin, Ohio. Standardized as IETF RFC 2413 (1998), ANSI/NISO Z39.85, and ISO 15836 (2003).

**Purpose**: Provide a simple, universal metadata vocabulary that non-specialists could use to describe web resources. Where MARC requires trained catalogers and complex software, Dublin Core was designed for anyone to apply.

**The 15 core elements**:

| # | Element | Definition |
|---|---------|------------|
| 1 | Title | Name given to the resource |
| 2 | Creator | Entity primarily responsible for making the resource |
| 3 | Subject | Topic of the resource |
| 4 | Description | Account of the resource content |
| 5 | Publisher | Entity responsible for making the resource available |
| 6 | Contributor | Entity responsible for making contributions |
| 7 | Date | Point or period associated with the resource lifecycle |
| 8 | Type | Nature or genre of the resource |
| 9 | Format | File format, physical medium, or dimensions |
| 10 | Identifier | Unambiguous reference to the resource (ISBN, URL, DOI) |
| 11 | Source | Related resource from which the resource is derived |
| 12 | Language | Language of the resource |
| 13 | Relation | Reference to a related resource |
| 14 | Coverage | Spatial or temporal topic of the resource |
| 15 | Rights | Information about rights held in and over the resource |

**Why it became the web standard**: Dublin Core succeeded because of deliberate design choices:

- **Simplicity**: 15 elements are learnable in minutes. MARC has hundreds of fields.
- **Optionality**: All elements are optional and repeatable. No minimum metadata requirements.
- **Domain-independence**: Elements are generic enough for any type of resource.
- **Extensibility**: Qualified Dublin Core allows refinement elements and encoding schemes without breaking the core vocabulary.
- **Embeddability**: Dublin Core maps naturally to HTML meta tags, RDF, and XML.

**Qualified Dublin Core** extends the 15 elements with refinements (e.g., `Date.Created`, `Date.Modified`) and encoding schemes (e.g., specifying that a Subject value uses LCSH vocabulary). This provides precision when needed without complicating the base standard.

### 2.3 FRBR (Functional Requirements for Bibliographic Records)

**Origin**: IFLA study group, published 1998. Now superseded by the IFLA Library Reference Model (LRM, 2017), which consolidates FRBR with related models FRAD and FRSAD.

**Core concept**: FRBR models bibliographic resources as a four-level hierarchy of entities called **WEMI**:

```
Work (abstract intellectual creation)
  └── Expression (specific intellectual realization)
        └── Manifestation (physical embodiment)
              └── Item (single physical exemplar)
```

**The four levels explained**:

**Work**: The highest level of abstraction — a distinct intellectual or artistic creation. Shakespeare's *Hamlet* as a conceptual entity, independent of any particular text, performance, or edition. A Work has no physical form; it is recognized through its Expressions.

**Expression**: The intellectual or artistic realization of a Work in a specific form — the text in a particular language, a specific musical performance, a translation, an abridgment. The original English text of *Hamlet* is one Expression; a German translation is another; a film adaptation might be considered another Expression of the same Work (though this boundary is debated).

**Manifestation**: The physical embodiment of an Expression — all copies that share the same content and physical characteristics. The 2003 Penguin paperback edition of *Hamlet* in English is a Manifestation. A different publisher's edition of the same English text is a different Manifestation of the same Expression.

**Item**: A single physical exemplar of a Manifestation — one specific copy of that 2003 Penguin *Hamlet*, with its own condition, location, ownership history, and annotations.

**Why FRBR matters**: Before FRBR, library catalogs treated each edition, translation, and format as an independent record with no formal relationship to other versions of the same work. A search for "Hamlet" might return dozens of records with no indication that they all represent the same underlying work. FRBR provides the conceptual model for **collocation** — grouping related items so users can navigate from a work to its various expressions, manifestations, and available copies.

**User tasks**: FRBR was explicitly designed around four user tasks:
1. **Find** — locate resources matching search criteria
2. **Identify** — confirm that a found resource is the one sought
3. **Select** — choose among multiple resources meeting the need
4. **Obtain** — acquire or access the selected resource

### 2.4 RDA (Resource Description and Access)

**Origin**: Published 2010, developed by the Joint Steering Committee (now RDA Steering Committee). Widely implemented in 2013 by the Library of Congress, British Library, and other major institutions.

**What it replaces**: RDA is the successor to AACR2 (Anglo-American Cataloguing Rules, 2nd edition), which had been the dominant descriptive cataloging standard since 1978.

**Key differences from AACR2**:

- **FRBR-based**: RDA's structure maps directly to the FRBR entity-relationship model. Cataloging instructions are organized by WEMI entity and by the user tasks (find, identify, select, obtain) rather than by material format.
- **Content vs. carrier**: RDA separates the description of intellectual content from the description of its physical carrier. AACR2 used a "class of materials" approach that mixed content and format considerations.
- **Format-agnostic**: Designed to describe any type of resource (analog, digital, born-digital) using the same principles, whereas AACR2 was primarily designed for print materials.
- **Linked data compatible**: RDA is designed with the semantic web in mind. RDA elements are registered as an RDF vocabulary, enabling RDA-compliant records to participate in linked data ecosystems.
- **Less prescriptive**: RDA provides guidelines and principles rather than rigid rules, giving catalogers more flexibility while maintaining consistency through shared vocabularies.
- **Internationalization**: RDA is designed for international use, removing Anglo-American specific assumptions.

### 2.5 Controlled Vocabularies and Authority Control

**The problem**: Without coordination, different catalogers describing the same entity will use different forms: "Mark Twain" vs. "Samuel Clemens" vs. "Twain, Mark, 1835-1910" vs. "Clemens, Samuel Langhorne." Users searching for one form will miss records using another. Synonyms, spelling variations, transliterations, name changes, and ambiguity create retrieval failures.

**Controlled vocabulary**: A managed list of authorized terms where each concept is represented by exactly one preferred term, with cross-references from variant forms. When you establish that "Cookery" is the authorized heading, you create "see" references from "Cooking," "Food preparation," etc., so that searches on any variant redirect to the canonical term.

**Authority control**: The process of maintaining controlled vocabularies at scale. Each authorized form is stored in an **authority record** that contains:

- The authorized (preferred) form of the heading
- Variant forms ("see" references)
- Related headings ("see also" references)
- Scope notes explaining usage
- Source citations justifying the choice
- A persistent identifier

**Key authority systems**:

- **LCCN (Library of Congress Control Number)**: Unique identifier assigned to each Library of Congress authority record. Functions as a persistent, unambiguous identifier for a name, subject, or series.
- **VIAF (Virtual International Authority File)**: International service that links national authority files from libraries worldwide. A single VIAF ID (e.g., VIAF: 107032638) connects all the variant forms of an entity's name across the Library of Congress, Bibliothèque nationale de France, Deutsche Nationalbibliothek, and dozens of other national libraries.
- **ISNI (International Standard Name Identifier)**: ISO standard providing persistent identifiers for creators and contributors.

**Why consistent naming matters**: Authority control is arguably the single most important quality control mechanism in library cataloging. Without it:

- Searches return incomplete results (missing records using different name forms)
- Searches return false matches (different people with similar names conflated)
- Collocating an author's complete works becomes impossible
- Linking between systems fails because there is no agreed-upon identifier

### Cataloging Standards — Implications for AI Knowledge Management

| Library Concept | METIS Application |
|-----------------|-------------------|
| MARC field structure | Structured metadata schema for knowledge items: fixed fields (type, tier, project) plus variable fields (content, context, relationships). |
| Dublin Core simplicity | Minimal required metadata for every knowledge item. Optional fields for enrichment. Low barrier to capture, rich capability for retrieval. |
| FRBR WEMI hierarchy | Knowledge at multiple abstraction levels: a Pattern (Work) may have multiple Articulations (Expressions) in different projects, stored in different Formats (Manifestations), with specific Instances (Items) accessed in sessions. |
| RDA content/carrier separation | Separate the knowledge content from its storage format. The same insight can live in a vault doc, a database row, a session fact, or an embedding — these are carriers of the same content. |
| Authority control | Canonical identifiers for projects, components, patterns, and concepts. Without this, the same concept stored under different names fragments retrieval. The `column_registry` and controlled vocabularies in METIS serve this function. |
| VIAF cross-system linking | Cross-project knowledge linking. The same concept appearing in multiple projects needs a shared identifier so retrieval can collate across boundaries. |

---

## 3. Retrieval and Discovery

Classification and cataloging create the infrastructure; retrieval and discovery are how users actually find what they need.

### 3.1 Subject Headings (LCSH) vs. Keywords

**Library of Congress Subject Headings (LCSH)**: The dominant controlled vocabulary for subject access in library catalogs, in continuous publication since 1909. LCSH assigns standardized terms to represent the subject content of library materials.

**How LCSH works**:

- **Pre-coordination**: Subject headings combine multiple concepts into a single string. "Women — Employment — United States — History — 20th century" is a single pre-coordinated heading.
- **Subdivisions**: Headings can be refined with topical, geographic, chronological, and form subdivisions.
- **Cross-references**: "Broader Term" (BT), "Narrower Term" (NT), and "Related Term" (RT) references connect headings into a syndetic structure.
- **Specificity**: A work is assigned the most specific heading that covers its content (following Cutter's principle of specific entry), not a broader term that merely includes it.

**Keywords** are uncontrolled, natural-language terms extracted from or assigned to a document without reference to any authority list. They capture the actual language authors and users employ.

**Critical differences**:

| Dimension | Subject Headings (LCSH) | Keywords |
|-----------|------------------------|----------|
| Vocabulary | Controlled, one preferred term per concept | Uncontrolled, any term |
| Consistency | Same concept always uses same term | Same concept may use many different terms |
| Recall | High — synonyms redirect to preferred term | Variable — misses synonym variants |
| Precision | High — terms are unambiguous | Lower — homonyms create false matches |
| Currency | Lags behind emerging terminology | Immediately reflects current usage |
| Cost | High — requires trained catalogers | Low — can be automated or user-generated |
| Serendipity | Structured browsing via BT/NT/RT | No structured navigation |

**The hybrid reality**: Modern library systems use both. Subject headings provide structured, reliable access; keyword search over full text and metadata catches what structured headings miss. The most effective discovery systems combine controlled vocabulary precision with keyword flexibility.

### 3.2 Faceted Search and Navigation

**Definition**: Faceted search allows users to filter and narrow search results along multiple independent dimensions (facets) simultaneously, without requiring them to formulate complex queries in advance.

**How it works in modern library catalogs**: After an initial search returns results, the system presents facet panels showing the distribution of results across categories like:

- **Format**: Book, Journal Article, DVD, Electronic Resource
- **Date**: Publication date ranges
- **Language**: English, Spanish, Chinese, etc.
- **Subject**: Derived from subject headings
- **Author**: From authority-controlled names
- **Library/Location**: Which branch holds the item
- **Availability**: Currently available, checked out, on order

Users click facet values to progressively narrow results. Each selection updates the available facet values, preventing "zero result" dead ends. The user never needs to know the classification scheme or controlled vocabulary — the facets are derived from the structured metadata automatically.

**Intellectual lineage**: Faceted search in digital interfaces is a direct descendant of Ranganathan's facet analysis. The key insight — that subjects have multiple independent dimensions and users should be able to approach from any dimension — translates directly from card-catalog theory to web interface design.

**Power of faceted navigation**: Unlike hierarchical browsing (which forces a single path through a classification tree) or Boolean search (which requires the user to formulate a complete query up front), faceted search supports **exploratory information seeking** — the user does not need to know exactly what they want at the start.

### 3.3 Citation Linking

**The problem**: Academic knowledge is not a collection of independent documents — it is a network of works that cite, extend, critique, and build upon each other. Traditional library catalogs treated each item as isolated, with no systematic way to trace intellectual lineages.

**Citation indexes**: Eugene Garfield's Science Citation Index (1964) pioneered systematic tracking of cited references. For any article, you could look up both what it cited and what later articles cited it — enabling forward and backward navigation through the knowledge network.

**OpenURL and link resolvers**: The OpenURL standard (ANSI/NISO Z39.88) enables context-sensitive linking between resources. When a user finds a citation in one database, the link resolver:

1. Receives the citation metadata as an OpenURL
2. Checks the library's **knowledge base** (a database of the library's subscriptions and holdings)
3. Constructs links to the full text on platforms the library has access to
4. Presents options to the user: full text links, catalog lookup, interlibrary loan request

**Link resolver knowledge bases** are extensive databases mapping journal titles, ISSNs, date ranges, and URLs to the library's specific subscriptions. They answer the question: "Given this citation, where can THIS library's users get it?"

**Modern citation networks**: Tools like Google Scholar, Semantic Scholar, and OpenAlex build large-scale citation graphs that enable:

- Forward citation tracking ("who cited this?")
- Citation-based relevance ranking (highly cited = more prominent)
- Related article discovery based on citation overlap
- Author and institution impact metrics

### 3.4 OPAC Evolution

**First generation (1960s-1970s)**: Online Public Access Catalogs replaced physical card catalogs with searchable databases, but early OPACs offered only exact-match searching on author, title, subject, and call number — essentially electronic versions of the card catalog.

**Second generation (1980s-1990s)**: Added keyword searching, Boolean operators, truncation, and browsable indexes. Still required users to understand search syntax and the catalog's structure.

**Third generation / Discovery layers (2000s-present)**: Inspired by web search engines, discovery layers provide:

- **Single search box**: Google-like simplicity replacing complex multi-field forms
- **Relevance ranking**: Results ordered by relevance rather than alphabetically or by date
- **Faceted narrowing**: Post-search filtering by format, date, subject, availability
- **Spell correction and suggestions**: "Did you mean..."
- **Unified index**: Searching across the library catalog, article databases, institutional repository, and digital collections simultaneously
- **Enriched displays**: Cover images, reviews, recommendations, availability status

**Major discovery platforms**:

- **Primo** (Ex Libris): Combines a local catalog index with Primo Central, a massive pre-harvested article-level index
- **Summon** (ProQuest/Ex Libris): Unified index approach emphasizing article-level discovery
- **WorldCat** (OCLC): Union catalog of holdings from libraries worldwide, now with WorldCat Discovery interface
- **EBSCO Discovery Service**: Leverages EBSCO's extensive database content

### 3.5 Relevance Ranking in Library Systems vs. Simple Boolean

**Boolean retrieval**: Traditional library search used Boolean logic (AND, OR, NOT) to produce unranked result sets. A document either matched or it did not. Results were typically sorted by date or alphabetically. This model is precise but unforgiving — a single mismatched term produces no results, and successful queries often return overwhelming unranked lists.

**Relevance ranking**: Modern discovery layers use algorithms derived from information retrieval research:

- **TF-IDF (Term Frequency-Inverse Document Frequency)**: Terms that appear frequently in a document but rarely across the collection are weighted more heavily.
- **BM25**: A refined probabilistic model that accounts for document length and term saturation. Widely used in library discovery systems.
- **Field weighting**: Matches in the title field are weighted more heavily than matches in notes. Subject heading matches may be weighted differently from keyword matches in full text.
- **Popularity signals**: Circulation data, click-through rates, and citation counts can boost relevance.
- **Recency**: More recent publications may receive a relevance boost in certain contexts.
- **Availability**: Some systems boost items that are currently available for checkout.

**The tension**: Librarians have debated whether relevance ranking helps or hinders discovery. Boolean search is transparent and reproducible — the same query always returns the same results. Relevance ranking is opaque — users cannot easily understand why results are ordered as they are. For known-item searching, Boolean is often more effective. For exploratory searching, relevance ranking is usually superior.

### Retrieval and Discovery — Implications for AI Knowledge Management

| Library Concept | METIS Application |
|-----------------|-------------------|
| LCSH structured access | Knowledge typed and tagged with controlled terms for reliable retrieval. Prevents the "I stored it under 'config' but searched for 'configuration'" problem. |
| Keyword flexibility | Embedding-based semantic search (Voyage AI) captures meaning beyond exact terms. Combines the flexibility of keywords with the recall benefits of controlled vocabularies. |
| Faceted search | Multi-dimensional filtering: by project, by tier (short/mid/long), by type (pattern/decision/fact), by recency, by confidence. Users should be able to narrow from any dimension. |
| Citation linking | Knowledge items linked by relationships: "derived from," "supersedes," "contradicts," "applies to." The `knowledge_links` table enables forward and backward traversal. |
| Discovery layers | A unified search interface that queries across all knowledge stores (session facts, working knowledge, long-term patterns, vault documents, workfiles) and returns ranked, faceted results. |
| Relevance ranking | Budget-capped retrieval (`recall_memories`) already does this: scoring by semantic similarity, recency, access frequency, and tier. This is the AI equivalent of library relevance ranking. |

---

## 4. Special Collections and Reserve Systems

Libraries manage not just general collections but also materials with special access requirements, high demand, or cross-boundary availability.

### 4.1 Reserve Collections

**Purpose**: Reserve collections surface high-demand items for current, intensive use. Academic libraries place items on "reserve" at faculty request, making them available for short loan periods (typically 2-24 hours) to ensure that a single copy can serve an entire class.

**Types of reserves**:

- **Course reserves**: Items directly supporting current courses, selected by instructors
- **Electronic reserves (e-reserves)**: Digital copies or links to licensed content, accessible 24/7
- **Permanent reserves**: Items always in high demand regardless of course schedules (reference works, popular titles)

**Key characteristics**:

- **Demand-driven surfacing**: Items are placed on reserve because of current, active need — not because of their inherent importance.
- **Temporal scoping**: Course reserves are typically active for one semester, then returned to general circulation.
- **Access modification**: Reserve items have shortened loan periods and often restricted borrowing (in-library use only).
- **Prominent placement**: Reserve collections are typically near the circulation desk, maximizing visibility and access.

**Parallel to `is_pinned` in METIS**: The `is_pinned` flag on project workfiles serves exactly the same function as library reserves — surfacing specific items for current need during active sessions, regardless of their position in the broader knowledge hierarchy.

### 4.2 Special Collections

**Definition**: Materials requiring different handling due to rarity, fragility, monetary value, or research significance. Includes rare books, manuscripts, archives, maps, photographs, and unique artifacts.

**Different cataloging rules**: Special collections often receive more detailed cataloging than general collections:

- **Provenance notes**: Recording ownership history, bookplates, inscriptions
- **Physical description**: Binding materials, paper type, illustrations, damage
- **Copy-specific notes**: What makes this particular copy unique
- **Restriction notes**: Access conditions, conservation concerns, donor restrictions

**Access model**: Typically "closed stacks" — materials do not circulate and must be used in a supervised reading room. Some items require advance appointment, researcher credentials, or donor approval.

**Finding aids**: Archival collections (groups of related documents from a person or organization) are described through **finding aids** — hierarchical inventories that describe the collection at multiple levels (collection, series, box, folder, item) without necessarily cataloging each individual document.

### 4.3 Interlibrary Loan (ILL)

**Definition**: A cooperative service through which libraries make materials from their collections available to users of other libraries. No single library can own everything; ILL enables access across institutional boundaries.

**How it works**:

1. A user requests an item their library does not hold
2. The library searches union catalogs (WorldCat, regional consortia) to identify holding libraries
3. A request is sent to a holding library via standardized protocols (ISO 10160/10161, OCLC ILL)
4. The lending library ships the physical item or transmits a digital copy
5. The borrowing library makes it available to the user (often with restrictions — no renewals, in-library use only for some materials)

**Standards and protocols**:

- **ISO ILL Protocol**: International standard for ILL message exchange
- **OCLC WorldShare ILL**: The dominant system in North America, processing millions of requests annually
- **RAPID**: A high-speed resource sharing system for article delivery
- **HathiTrust Emergency Temporary Access**: Digital lending model pioneered during COVID-19

**Cross-boundary knowledge parallel**: ILL is the library equivalent of cross-project knowledge retrieval in METIS. Knowledge that exists in one project's context may be needed by another. The `client_domain` grouping and cross-project search capabilities serve this function.

### 4.4 Stacks Management

**Open stacks vs. closed stacks**:

- **Open stacks**: Users browse shelves directly. Enables serendipitous discovery (finding unexpected relevant items shelved near what you were looking for). Most public and academic libraries use open stacks for general collections.
- **Closed stacks**: Staff retrieve requested items. Used for rare materials, high-security areas, and high-density storage. Prevents theft and damage but eliminates browsing.

**Call number arrangement**: Items on shelves are arranged by call number (classification number + Cutter number), which groups items by subject. This physical arrangement is a form of **collocation** — bringing related items together.

**Storage tiers**: Large research libraries often use tiered storage:

- **Active stacks**: Open, accessible, well-lit — for frequently used materials
- **Compact shelving**: High-density movable shelving — for less-used but still needed materials
- **Off-site storage**: Remote facilities with environmental controls — for rarely used materials, retrievable on request (typically 24-48 hour delivery)

This tiering by access frequency directly parallels memory hierarchy in computing and in METIS's three-tier memory system (short/mid/long).

### Special Collections — Implications for AI Knowledge Management

| Library Concept | METIS Application |
|-----------------|-------------------|
| Reserve collections | `is_pinned` workfiles and high-priority session facts surfaced at session start. Demand-driven, temporally scoped. |
| Special collections cataloging | Sensitive credentials, architectural decisions, and system-critical patterns may need richer metadata, access restrictions, and provenance tracking. |
| Interlibrary loan | Cross-project knowledge sharing via `client_domain` grouping and cross-domain search. Knowledge does not need to be duplicated — it can be retrieved across boundaries. |
| Storage tiers (active/compact/off-site) | SHORT/MID/LONG memory tiers. Session facts (active stacks), working knowledge (compact shelving), proven patterns (off-site but indexed for retrieval). ARCHIVED tier = withdrawn from active access. |
| Open vs. closed stacks | Some knowledge is browsable (recall_memories returns candidates for exploration). Some is restricted (sensitive credentials require explicit request). |

---

## 5. Digital Library Science

The transition from physical to digital collections introduces new challenges and opportunities for knowledge organization.

### 5.1 Linked Open Data and the Semantic Web in Libraries

**The problem with traditional library data**: MARC records are designed for library-to-library exchange. They are opaque to web search engines, isolated from the broader information ecosystem, and trapped in library-specific systems.

**Linked data principles** (Tim Berners-Lee, 2006):

1. Use URIs as names for things
2. Use HTTP URIs so people can look up those names
3. Provide useful information when someone looks up a URI (using RDF, SPARQL)
4. Include links to other URIs so people can discover more things

**BIBFRAME (Bibliographic Framework Initiative)**: Developed by the Library of Congress as the successor to MARC for the linked data environment. BIBFRAME models bibliographic data using three core classes:

- **Work**: The conceptual essence of the cataloged resource
- **Instance**: A material embodiment of a Work (roughly combining FRBR's Expression and Manifestation)
- **Item**: An actual copy (same as FRBR's Item)

BIBFRAME simplifies FRBR's four levels to three and expresses all relationships as RDF triples, making library data native to the semantic web.

**SKOS (Simple Knowledge Organization System)**: A W3C standard for expressing controlled vocabularies (thesauri, classification schemes, subject heading systems) as linked data. LCSH, DDC, and other library vocabularies have been published in SKOS format, making them linkable and queryable across the web.

**Adoption**: Major national libraries (Library of Congress, BnF, DNB, British Library, Swedish National Library) have published significant linked open data sets. The practical transition from MARC to BIBFRAME is ongoing but far from complete — the scale of existing MARC infrastructure creates enormous inertia.

### 5.2 Digital Preservation

**The challenge**: Digital objects are far more fragile than physical ones. A book on a shelf remains readable for centuries with no active intervention. A digital file becomes inaccessible when its format becomes obsolete, its storage medium degrades, or its delivery platform disappears.

**OAIS Reference Model (Open Archival Information System)**: ISO 14721, originally developed by the Consultative Committee for Space Data Systems (CCSDS) and now the foundational framework for digital preservation worldwide.

**OAIS functional entities**:

| Function | Purpose |
|----------|---------|
| **Ingest** | Accept content from producers, perform quality assurance, generate archival packages |
| **Archival Storage** | Store and maintain archival packages, provide retrieval |
| **Data Management** | Maintain descriptive metadata, enable search and retrieval |
| **Administration** | Manage day-to-day operations, policies, standards |
| **Preservation Planning** | Monitor the designated community and technology environment, develop preservation strategies |
| **Access** | Provide delivery to consumers, enforce access controls |

**Information packages**: OAIS defines three types:

- **SIP (Submission Information Package)**: What the content producer delivers to the archive
- **AIP (Archival Information Package)**: What the archive stores — the content plus all metadata needed for long-term preservation
- **DIP (Dissemination Information Package)**: What the archive delivers to consumers — potentially transformed or reformatted from the AIP

**Preservation strategies**:

- **Migration**: Converting content from obsolete formats to current ones (e.g., WordPerfect to PDF/A)
- **Emulation**: Running obsolete software in emulated environments to render original formats
- **Normalization**: Converting all incoming content to a small set of preservation-quality formats at ingest time
- **Format registries**: PRONOM (The National Archives, UK) and the Global Digital Format Registry provide technical information about file formats to support preservation decisions

### 5.3 Institutional Repositories

**Definition**: Digital archives for collecting, preserving, and disseminating the intellectual output of an institution (typically a university). They make research outputs openly accessible, fulfilling open access mandates and preserving institutional knowledge.

**Major platforms**:

**DSpace**: The most widely deployed institutional repository platform globally. Originally developed by MIT and HP Labs. Java-based, well-established, strong community support. Uses a simple data model: Community → Collection → Item → Bitstream (file). Strong metadata support via Dublin Core. Newer versions support configurable entity models.

**Fedora (Flexible Extensible Digital Object Repository Architecture)**: A highly flexible data storage platform with native linked data (RDF) support. Fedora is not a complete repository application — it is an infrastructure layer. Most institutions use it through higher-level frameworks:

- **Samvera (formerly Hydra)**: Ruby on Rails applications built on Fedora, providing customizable repository solutions
- **Islandora**: Drupal-based front end on Fedora, combining content management flexibility with robust digital object storage

**Key considerations for repository selection**: Local technical capacity, collection types, metadata complexity, integration requirements, and community support. DSpace is suited for straightforward institutional repositories; Fedora-based solutions offer more flexibility for complex digital library projects but require more development expertise.

### 5.4 Knowledge Organization Systems (KOS)

**Definition**: Any system used to organize and manage knowledge. KOS form a spectrum from informal to formal:

| Type | Complexity | Structure | Example |
|------|-----------|-----------|---------|
| **Folksonomy** | Lowest | User-generated tags, no hierarchy or control | Del.icio.us tags, library catalog user tags |
| **Term list** | Low | Flat list of preferred terms | Glossary, dictionary |
| **Taxonomy** | Medium | Hierarchical arrangement of terms | Biological classification, website navigation |
| **Thesaurus** | Medium-High | Hierarchical + associative relationships (BT/NT/RT), scope notes | LCSH, MeSH (Medical Subject Headings) |
| **Ontology** | Highest | Formal logic, defined relationships, inference rules | OWL ontologies, BIBFRAME, Schema.org |

**Key distinctions**:

- **Taxonomy vs. Thesaurus**: A taxonomy shows hierarchical (is-a) relationships. A thesaurus adds associative (related-to) relationships and equivalence (synonym) relationships, plus scope notes defining terms.
- **Thesaurus vs. Ontology**: A thesaurus defines terms and their relationships for human use. An ontology defines classes, properties, and relationships with formal semantics that support automated reasoning (inference).
- **Folksonomy vs. Controlled vocabulary**: Folksonomies capture the actual language of users (high currency, low consistency). Controlled vocabularies impose consistency at the cost of currency and user effort.

**Hybrid approaches**: Modern systems often combine multiple KOS types. Library catalogs use controlled vocabularies (LCSH) alongside user-generated tags. Search systems use formal ontologies for entity recognition while supporting free-text keyword search.

### Digital Library Science — Implications for AI Knowledge Management

| Library Concept | METIS Application |
|-----------------|-------------------|
| Linked Open Data | Knowledge items with URIs (or persistent IDs) that can be dereferenced to retrieve structured metadata and linked to related items across systems. |
| BIBFRAME Work/Instance/Item | Knowledge patterns (Work) with project-specific instantiations (Instance) and session-specific retrievals (Item). |
| OAIS information packages | Submission (user provides raw knowledge), Archival (system stores with embeddings, metadata, provenance), Dissemination (system delivers budget-capped, formatted for context). |
| Format migration | Knowledge stored in format-independent representations (structured data, embeddings) rather than tied to specific file formats or tool versions. |
| Institutional repositories | Each project has its own knowledge repository (workfiles, component context). Cross-project search enables institutional-level discovery. |
| KOS spectrum | METIS currently uses a mix: folksonomy (user-supplied tags), taxonomy (project/domain/tier hierarchy), and lightweight ontology (knowledge_links with typed relationships). Moving toward richer thesaurus-level relationships would improve retrieval. |
| Folksonomy + controlled vocabulary hybrid | Allow users to tag freely (low friction capture) while system normalizes to controlled terms in the background (reliable retrieval). |

---

## 6. Key Principles That Translate to AI Knowledge Management

### 6.1 Ranganathan's Five Laws of Library Science (1931)

These five laws are the most influential statement of library philosophy ever formulated. They are principles, not rules — they describe the purpose and direction of library service.

**First Law: Books are for use.**

In Ranganathan's time, many libraries treated their collections as treasures to be preserved rather than resources to be used. Books were kept in closed stacks, access was restricted, and the emphasis was on custody rather than service. The First Law asserts that the purpose of a library is to make its materials used, not merely to house them.

*METIS application*: Knowledge stored is worthless if it is not retrievable and actionable. The system must optimize for knowledge *use*, not just knowledge *storage*. This means: fast retrieval (budget-capped recall), automatic surfacing (session start injection, pinned workfiles), and low-friction access (semantic search, not requiring exact terms). Every feature that increases storage without increasing usability violates this law.

**Second Law: Every reader his or her book.**

Every person with an information need should be able to find material that meets that need. This law drives collection development (acquiring diverse materials), user services (helping people navigate the collection), and access policies (removing barriers).

*METIS application*: Every agent or session should find the knowledge relevant to its current task. This means knowledge must be tagged with sufficient context (project, domain, tier) and retrievable from multiple angles (semantic similarity, faceted filtering, relationship traversal). If an agent cannot find relevant knowledge that exists in the system, the system has failed this law.

**Third Law: Every book its reader.**

The complement of the Second Law. Not only should every user find their material — every piece of material should find its user. This drives proactive recommendation, displays, reading lists, and outreach.

*METIS application*: Knowledge should be proactively surfaced when relevant, not just passively available for search. The RAG hook, pinned workfiles at session start, and `recall_memories()` with proactive context injection all serve this law. Knowledge that exists but is never surfaced is a failure of the Third Law. This argues for recommendation systems: "You are working on X; here is knowledge from project Y that is relevant."

**Fourth Law: Save the time of the reader.**

Everything about the library — classification, cataloging, reference service, physical layout — should minimize the time users spend finding and accessing what they need.

*METIS application*: Budget-capped retrieval, pre-compaction injection, and automated context loading all serve this law. The user should not need to manually search for context that the system can predict they need. Redundant or low-value results waste context window space (the AI equivalent of the reader's time). Ranking, deduplication, and budget management are implementations of the Fourth Law.

**Fifth Law: The library is a growing organism.**

Libraries are not static — they grow in collections, in services, in physical space, and in the needs they serve. The library must be designed to accommodate growth without requiring complete reorganization.

*METIS application*: The knowledge system must accommodate growth in projects, domains, knowledge types, and agents without architectural overhaul. Faceted classification (not fixed hierarchy), extensible metadata schemas, and tiered storage with lifecycle management (consolidation, promotion, archival) all serve this law. A system designed only for current scale will fail as knowledge accumulates.

### 6.2 Principle of Literary Warrant

**Definition**: Classification categories and subject headings should be created based on the literature that actually exists, not on theoretical completeness. A class should be established only when there are actual documents to place in it.

*METIS application*: Do not pre-build elaborate knowledge taxonomies. Create categories, tags, and relationship types based on knowledge that actually gets stored. If no knowledge items use a category, it is dead weight. Let the system's organization emerge from its content. This principle argues against designing a complete knowledge ontology up front and instead building it incrementally as warranted by actual stored knowledge.

### 6.3 Principle of Specific Entry

**Definition**: A work should be entered under the most specific subject heading that describes its content, not under a broader heading that merely includes it. A book about cats should be entered under "Cats," not under "Domestic animals" or "Mammals."

*METIS application*: Knowledge items should be tagged and classified at the most specific level that accurately represents their content. A decision about PostgreSQL connection pooling should be stored under "PostgreSQL connection pooling," not under "database" or "infrastructure." Overly broad tagging makes retrieval imprecise — the user searching for connection pooling information should not have to wade through all database knowledge. Embeddings naturally serve this principle (they capture specific meaning), but structured tags and categories must also follow it.

### 6.4 Principle of Collocation

**Definition**: Items that are related should be brought together in the catalog, so that a user who finds one can discover the others. This applies to:

- **Works by the same author** (author collocation)
- **Different editions and translations of the same work** (work collocation, formalized by FRBR)
- **Works on the same subject** (subject collocation)
- **Works in the same series** (series collocation)

*METIS application*: Related knowledge items must be linked and co-retrievable. When an agent retrieves a pattern about "session lifecycle," the system should surface related items: the BPMN model, the hook implementations, past decisions about session behavior, known gotchas. The `knowledge_links` table, embedding-based similarity, and component-scoped workfiles all serve collocation. The danger is knowledge fragmentation — storing related items with no links between them, making each discoverable only by direct search.

### 6.5 Cutter's Rules for a Dictionary Catalog (1876)

Charles Ammi Cutter formulated the first systematic statement of catalog objectives. His three "Objects of the Catalog" remain foundational:

**First Object — Finding**: Enable a person to find a resource when they know the author, title, or subject.

**Second Object — Collocation**: Show what the library has by a given author, on a given subject, or in a given kind of literature.

**Third Object — Choice**: Assist in the choice of a resource as to its edition (bibliographically) or as to its character (literary or topical).

**Cutter's means for achieving these objects**:

- **Author entry under the name most commonly known** (not necessarily the "real" name)
- **Title entry for anonymous works and works known primarily by title**
- **Subject entry under the most specific term** (the Principle of Specific Entry)
- **Cross-references** connecting variant forms, related subjects, and broader/narrower terms

*METIS application*: The knowledge system must support three distinct retrieval modes:

1. **Finding** (known-item search): "I know this pattern exists, find it by name/keyword." Fast, precise, high-confidence matches.
2. **Collocation** (related-item discovery): "Show me everything related to session management." Broader, relationship-following, context-building.
3. **Choice** (selection assistance): "Here are 5 relevant items — which is most applicable to your current situation?" Ranking, recency weighting, confidence scoring, tier indication.

These map directly to different query strategies in `recall_memories()`: exact match for finding, semantic search for collocation, ranked/budget-capped results for choice.

---

## Summary: A Library Science Framework for AI Knowledge Management

The following table maps the full spectrum of library science concepts to their AI knowledge management equivalents:

| Library Science Layer | Traditional Library | AI Knowledge System (METIS) |
|-----------------------|--------------------|-----------------------------|
| **Classification** | DDC/LCC/UDC call numbers | Project + domain + tier + type facets |
| **Faceted analysis** | Ranganathan PMEST, BC2 categories | Multi-dimensional metadata: who, what, when, where, why, confidence |
| **Cataloging** | MARC records, Dublin Core | Structured knowledge records with required + optional metadata |
| **Authority control** | LCCN, VIAF, LCSH | `column_registry`, canonical project/component names, controlled vocabularies |
| **Abstraction hierarchy** | FRBR WEMI | Pattern → Articulation → Storage → Instance |
| **Subject access** | LCSH headings + keywords | Controlled tags + embedding-based semantic search |
| **Discovery** | OPAC / discovery layers | `recall_memories()` with faceted, ranked, budget-capped results |
| **Citation linking** | OpenURL, citation indexes | `knowledge_links` table with typed relationships |
| **Reserve collections** | Course reserves, e-reserves | `is_pinned` workfiles, session facts |
| **Storage tiers** | Active / compact / off-site stacks | SHORT / MID / LONG / ARCHIVED memory tiers |
| **Cross-boundary access** | Interlibrary loan | Cross-project search via `client_domain` |
| **Preservation** | OAIS, format migration | Format-independent storage, embedding re-generation |
| **Linked data** | BIBFRAME, SKOS, LOD | Knowledge graph with typed relationships and persistent IDs |
| **KOS spectrum** | Folksonomy → taxonomy → thesaurus → ontology | User tags → project hierarchy → controlled vocabulary → typed knowledge links |

The deepest lesson from library science is this: **the value of a knowledge system is determined not by how much it stores, but by how reliably and efficiently it delivers the right knowledge to the right user at the right time.** Every classification scheme, every cataloging standard, every retrieval mechanism, and every collection management practice exists to serve that goal. Ranganathan's laws — particularly "Save the time of the reader" and "Every book its reader" — should be the guiding principles for METIS's knowledge architecture.

---

## Sources

- [Colon Classification — Wikipedia](https://en.wikipedia.org/wiki/Colon_classification)
- [Colon Classification — ISKO Encyclopedia](https://www.isko.org/cyclo/colon_classification)
- [Colon Classification — Britannica](https://www.britannica.com/science/Colon-Classification)
- [FRBR — Wikipedia](https://en.wikipedia.org/wiki/Functional_Requirements_for_Bibliographic_Records)
- [FRBR — OCLC Research](https://www.oclc.org/research/activities/frbr.html)
- [FRBR, WEMI and MARC — Cataloging with MARC, RDA](https://csi.pressbooks.pub/cataloging/chapter/frbr-wemi/)
- [UDC Structure and Tables — UDC Consortium](https://udcc.org/index.php/site/page?view=about_structure)
- [Universal Decimal Classification — Wikipedia](https://en.wikipedia.org/wiki/Universal_Decimal_Classification)
- [Bliss Bibliographic Classification — Wikipedia](https://en.wikipedia.org/wiki/Bliss_bibliographic_classification)
- [BC2 History and Description — Bliss Classification Association](https://www.blissclassification.org.uk/bchist.shtml)
- [BC2 — ISKO Encyclopedia](https://www.isko.org/cyclo/bc2)
- [Dublin Core — Wikipedia](https://en.wikipedia.org/wiki/Dublin_Core)
- [DCMI Metadata Element Set](https://www.dublincore.org/specifications/dublin-core/dces/)
- [OAIS Reference Model — OCLC](https://www.oclc.org/research/publications/2000/lavoie-oais.html)
- [OAIS — Wikipedia](https://en.wikipedia.org/wiki/Open_Archival_Information_System)
- [Five Laws of Library Science — Wikipedia](https://en.wikipedia.org/wiki/Five_laws_of_library_science)
- [Ranganathan's Five Laws — LIS Academy](https://lis.academy/library-information-and-society/ranganathans-five-laws-modern-library-services/)
- [MARC Standards — Wikipedia](https://en.wikipedia.org/wiki/MARC_standards)
- [MARC 21 Formats — Library of Congress](https://www.loc.gov/marc/96principl.html)
- [LCSH — Wikipedia](https://en.wikipedia.org/wiki/Library_of_Congress_Subject_Headings)
- [Controlled Vocabularies — Library of Congress](https://www.loc.gov/librarians/controlled-vocabularies/)
- [Cutter's Objects of the Catalogue — Librarianship Studies](https://www.librarianshipstudies.com/2020/03/charles-ammi-cutters-objects-catalogue-objectives-library-catalog.html)
- [RDA — Wikipedia](https://en.wikipedia.org/wiki/Resource_Description_and_Access)
- [RDA — Librarianship Studies](https://www.librarianshipstudies.com/2017/07/resource-description-and-access-rda.html)
- [Authority Control — Wikipedia](https://en.wikipedia.org/wiki/Authority_control)
- [Discovery Systems — Wikipedia](https://en.wikipedia.org/wiki/Discovery_system_(bibliographic_search))
- [Faceted Search in Libraries — Taylor & Francis](https://www.tandfonline.com/doi/full/10.1080/01639374.2023.2222120)
- [DDC — Wikipedia](https://en.wikipedia.org/wiki/Dewey_Decimal_Classification)
- [DDC Introduction — OCLC](https://www.oclc.org/content/dam/oclc/dewey/versions/print/intro.pdf)
- [LCC vs DDC — Wikipedia](https://en.wikipedia.org/wiki/Comparison_of_Dewey_and_Library_of_Congress_subject_classification)
- [BIBFRAME — Library of Congress](https://www.loc.gov/aba/pcc/documents/LinkedData_LCIntro20150508.pdf)
- [Linked Data for Libraries — SAGE Journals](https://journals.sagepub.com/doi/10.1177/01655515221084645)
- [Islandora — Wikipedia](https://en.wikipedia.org/wiki/Islandora)
- [Institutional Repository Software Comparison — UBC](https://open.library.ubc.ca/soa/cIRcle/collections/graduateresearch/42591/items/1.0075768)

---

**Version**: 1.0
**Created**: 2026-03-10
**Updated**: 2026-03-10
**Location**: knowledge-vault/10-Projects/Project-Metis/research/library-science-research.md
