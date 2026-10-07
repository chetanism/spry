---
title: Domain code conventions
summary: results instead of exceptions, `today` passed in
applies_to: [src/loans/**, src/members/**]
audience: 8
---
# Domain code conventions

- Return `Result<T, E>`; never throw for a rule the desk shows to a librarian — the desk must show every refusal, and a thrown error loses its type.
- Take `today: LocalDate` as a parameter; never read the clock inside domain code — tests and B-1 need control over the date.
- One error type per refusal (`AtLimit`, `Overdue`, `AlreadyOnLoan`) — the desk maps each to its own message.
