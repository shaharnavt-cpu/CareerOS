# CareerOS Knowledge Model

## Purpose

CareerOS is built around structured career knowledge rather than documents.

The purpose of the knowledge model is to define every type of information CareerOS understands, stores, and reasons about.

All resumes, cover letters, interview preparation, networking messages, and recommendations are generated from this knowledge.

---

# Design Principles

## Single Source of Truth

Every fact should exist only once.

Documents should be generated from knowledge rather than acting as the primary source of information.

---

## Knowledge over Documents

CareerOS stores facts, relationships, outcomes, evidence, and user preferences.

Resumes, cover letters, interview answers, networking messages, and career summaries are generated views of that knowledge.

---

## Applications are the Core Entity

Applications are the central object in CareerOS.

Every application represents a snapshot of the user's career at a specific point in time.

Applications connect together:

* Job postings
* Resume versions
* Cover letters
* Questions answered
* Recruiters
* Interviews
* Assessments
* Outcomes
* Lessons learned
* Career insights

Applications are the primary source of learning for CareerOS.

---

# Core Knowledge Objects

## Person

Represents the user and long-term professional profile.

Examples include:

* Name
* Contact Information
* Education
* Work Authorization
* Graduation Date
* Career Goals
* Preferred Industries
* Preferred Locations
* Salary Preferences
* Skills
* Interests
* Resume Preferences

---

## Education

Represents formal education.

Examples:

* University
* Degree
* Major
* Minor
* GPA
* Scholarships
* Coursework
* Graduation Date

---

## Experience

Professional, research, volunteer, leadership, or teaching experience.

Examples:

* Internships
* Employment
* Research
* Teaching
* Leadership
* Volunteer Work

Each experience stores:

* Responsibilities
* Achievements
* Metrics
* Skills Demonstrated
* Supporting Evidence

---

## Project

Represents any technical, academic, research, hackathon, or personal project.

Each project stores:

* Description
* Technologies Used
* Skills Demonstrated
* Outcomes
* Metrics
* Screenshots
* GitHub Repository
* Documentation

---

## Achievement

Represents measurable accomplishments.

Examples:

* Awards
* Scholarships
* Conference Presentations
* Publications
* Leadership Growth
* Revenue Generated
* Members Recruited
* GPA Milestones

Achievements should always include supporting evidence whenever possible.

---

## Skill

Represents technical and non-technical abilities.

Examples:

* Python
* SQL
* Machine Learning
* Leadership
* Communication
* Public Speaking

Skills can be linked to:

* Experiences
* Projects
* Achievements
* Applications
* Interview Questions

---

## Company

Represents organizations the user interacts with.

Stores:

* Industry
* Headquarters
* Sponsorship Information
* Previous Applications
* Recruiter Contacts
* Notes
* Response History

---

## Job

Represents a specific job posting.

Stores:

* Company
* Role
* Job Description
* Requirements
* Salary
* Location
* Employment Type
* Application Deadline
* Original Posting URL

---

## Application

The central entity of CareerOS.

Each application represents a complete historical record.

Stores:

* Job
* Resume Version Used
* Cover Letter Used
* Questions Asked
* Answers Submitted
* Date Applied
* Current Status
* Recruiter
* Assessments
* Interviews
* Offer Details
* Outcome
* Reflection
* Lessons Learned

Applications are immutable snapshots that preserve exactly what was submitted at that point in time.

---

## Contact

Represents professional relationships.

Examples:

* Recruiters
* Hiring Managers
* Professors
* Alumni
* Mentors
* Networking Contacts

Stores:

* Contact Information
* Relationship
* Notes
* Communication History
* Follow-up Dates

---

## Timeline Event

Represents chronological career events.

Examples:

* Application Submitted
* Assessment Received
* Interview Scheduled
* Offer Received
* Rejection
* Networking Conversation
* Resume Updated
* Certification Earned

Timeline Events allow CareerOS to reconstruct the user's professional journey over time.

---

# Relationships

CareerOS is designed as a connected knowledge graph.

For example:

Person

↓

Experience

↓

Achievement

↓

Skill

↓

Project

↓

Application

↓

Interview

↓

Outcome

Rather than storing isolated documents, CareerOS stores relationships between knowledge objects.

---

# Reflection and Learning

Every completed application should contain a reflection section.

Examples:

* What worked well?
* What could be improved?
* Would I apply again?
* What interview questions were asked?
* Which resume version was used?
* Which cover letter was submitted?
* What feedback was received?
* What did I learn?

These reflections become valuable long-term knowledge that CareerOS can use to generate personalized recommendations.

---

# Guiding Principle

CareerOS does not remember files.

CareerOS remembers the user's professional journey.

Everything else can be regenerated from that knowledge.
