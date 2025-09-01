---
metadata:
  id: meeting_notes_standard
  name: Meeting Notes Template
  description: Structured meeting notes template
  category: misc
  type: meeting_notes
  version: 1.0.0
  author: DevDocAI
  tags: [meeting, notes, documentation, minutes]
variables:
  - name: meeting_title
    required: true
    type: string
  - name: date
    required: true
    type: string
  - name: facilitator
    required: true
    type: string
---

# {{meeting_title}}

**Date:** {{date}}  
**Time:** [Start time - End time]  
**Facilitator:** {{facilitator}}  
**Note Taker:** [Name]

## Attendees

- [Name] - [Role]
- [Name] - [Role]
- [Name] - [Role]

## Absent

- [Name] - [Role] - [Reason if known]

## Agenda

1. [Agenda item 1]
2. [Agenda item 2]
3. [Agenda item 3]
4. Action items review
5. Next steps

## Discussion Points

### [Topic 1]

- **Discussion:** Key points discussed
- **Decisions:** Decisions made
- **Concerns:** Any concerns raised

### [Topic 2]

- **Discussion:** Key points discussed
- **Decisions:** Decisions made
- **Concerns:** Any concerns raised

## Action Items

| Action | Assignee | Due Date | Status |
|--------|----------|----------|---------|
| [Action description] | [Name] | [Date] | Open |
| [Action description] | [Name] | [Date] | In Progress |

## Decisions Made

- **Decision 1:** [Description]
- **Decision 2:** [Description]

## Next Meeting

- **Date:** [Next meeting date]
- **Time:** [Time]
- **Agenda Items:** [Key items for next meeting]

## Follow-up Required

- [ ] Send meeting notes to all attendees
- [ ] Update project documentation
- [ ] Schedule follow-up meetings
- [ ] Track action item progress

---
**Meeting Notes By:** [Note taker name]  
**Distributed:** {{current_date}}
