# Requirements and Policy

## Purpose

This document defines the equipment-request policy for the internal IT handler. Later tools, unit tests, and the agent implement this policy. Rules below are deterministic as of a fixed evaluation date so expected outcomes can be tested.

**Evaluation date:** 2026-09-30

Age and tenure use calendar anniversaries against that date. A laptop assigned on 2024-08-15 is 2 years old on 2026-09-30. It becomes eligible for a 4-year refresh on 2028-08-15.

## Scenario

Employees submit equipment requests in natural language (for example, "I need a second monitor" or "my laptop is 4 years old and slow"). The system looks up the employee's role and equipment on file, checks that role's limits, and returns one of three decisions:

- **Approve** when the request is a single catalog item and the policy limits allow it.
- **Deny** when the request is a single catalog item and the policy limits forbid it.
- **Escalate** when the request is ambiguous, the data needed to apply policy is missing, or the employee asks for an exception. Escalated requests go to a human reviewer. The system records the escalation and leaves the decision open.



## Request data

A request the agent can decide contains:


| Field         | Source           | Required | Meaning                                                                            |
| ------------- | ---------------- | -------- | ---------------------------------------------------------------------------------- |
| `employee_id` | Requester        | Yes      | Directory key, format `E-####` (example `E-1001`).                                 |
| `item`        | Requester        | Yes      | One catalog item: `laptop`, `monitor`, `docking_station`, or `headset`.            |
| `reason`      | Requester        | Yes      | Free-text justification. Used to detect exceptions and vague wording.              |
| `quantity`    | Requester        | No       | Defaults to 1. A number above 1 is the count being asked for in this request.      |
| `role`        | Directory lookup | Yes      | Taken from employee records. The requester's claim about their role is ignored.    |
| `tenure`      | Directory lookup | Yes      | Time from `hire_date` to 2026-09-30.                                               |
| `equipment`   | Directory lookup | Yes      | Items already on file, each with `item` and `assigned_on` (`YYYY-MM-DD` or empty). |


The handler needs `employee_id`, a resolvable `item`, and a `reason` before it can approve or deny. Role, tenure, and equipment always come from the directory.

## Roles and catalog

Policy covers three roles:

- `individual_contributor`
- `manager`
- `director`

Any other role string, including `contractor`, has no limits on file.

Catalog items are `laptop`, `monitor`, `docking_station`, and `headset`. Wording that maps cleanly onto one of these (for example, "MacBook" or "display") counts as that item. Anything else is an unlisted item.

## Policy limits

Limits are per person and per item. `max_on_file` is the number of units that role may hold. `refresh` is how long a held unit must be assigned before it may be replaced.


| Role                   | Item            | Max on file | Refresh |
| ---------------------- | --------------- | ----------- | ------- |
| individual_contributor | laptop          | 1           | 4 years |
| individual_contributor | monitor         | 1           | 3 years |
| individual_contributor | docking_station | 1           | 4 years |
| individual_contributor | headset         | 1           | 2 years |
| manager                | laptop          | 1           | 2 years |
| manager                | monitor         | 2           | 3 years |
| manager                | docking_station | 1           | 3 years |
| manager                | headset         | 1           | 2 years |
| director               | laptop          | 1           | 2 years |
| director               | monitor         | 2           | 2 years |
| director               | docking_station | 1           | 2 years |
| director               | headset         | 1           | 1 year  |


There is no separate new-hire bundle. A first unit is allowed because the employee holds fewer than `max_on_file`.

## Eligibility rules

Apply these rules only after the request resolves to one catalog item for an employee whose role has a policy row, and only when every on-file unit of that item has an `assigned_on` date.

1. **Issuance.** When `units_on_file + quantity <= max_on_file`, the request is eligible. The refresh interval does not apply to units the employee does not yet hold. A manager with one monitor may receive a second monitor immediately.
2. **Replacement.** When the employee already holds `max_on_file` and `quantity` is 1, the request replaces the oldest unit. It is eligible when `oldest_assigned_on + refresh` is on or before 2026-09-30. The next eligible date is `oldest_assigned_on + refresh`.
3. **Over the maximum.** When `units_on_file + quantity > max_on_file` and rule 2 does not apply (quantity above 1, or the wording asks for an additional unit rather than a replacement), the request is ineligible with reason `exceeds_role_maximum`.

Replacement wording includes "replacement", "refresh", "new laptop" when they already hold one, and "this one is old". Additional-unit wording includes "second", "another", "additional", or a quantity that would raise the count above the max. A bare "monitor" from someone under the max is an issuance. A bare "monitor" from someone already at the max is a replacement.

## Decision outcomes


| Outcome  | When it applies                                                                                    | What the handler does                                                                                                        |
| -------- | -------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| Approve  | Eligibility rules say the single catalog item is allowed, and no escalation trigger below applies. | State the role, the limit used, and the supporting fact (units on file, or the oldest assignment date and refresh interval). |
| Deny     | Eligibility rules say the single catalog item is forbidden, and no escalation trigger applies.     | State `refresh_not_elapsed` or `exceeds_role_maximum`. For a refresh denial, include `next_eligible_date`.                   |
| Escalate | Any trigger in the next section matches.                                                           | Record the request for human review with one reason code. Leave approve and deny unset.                                      |


A clear denial is a completed decision. It is not sent to human review.

## Ambiguous cases

The following are escalation reason codes. Each one is sufficient on its owfn.


| Code                          | Trigger                                                                                                                                                             |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `unknown_employee`            | `employee_id` is absent from the directory.                                                                                                                         |
| `unknown_role`                | The employee exists and their role has no row in the policy table.                                                                                                  |
| `vague_item`                  | The text names zero catalog items, or a phrase that could be more than one item ("a computer", "something better", "new gear").                                     |
| `unlisted_item`               | The text names a concrete item outside the catalog (standing desk, tablet, phone, chair).                                                                           |
| `multiple_items`              | The text names two or more different catalog items.                                                                                                                 |
| `incomplete_equipment_record` | A held unit of the requested item has no `assigned_on`, and the decision depends on age (the employee is already at `max_on_file` and this would be a replacement). |
| `exception_language`          | The reason asks to waive policy or cites damage, theft, loss, defect, malfunction, medical need, accessibility, or safety.                                          |


`exception_language` covers requests that would otherwise be a clean denial. A laptop that is inside the refresh window and was "destroyed by a spill" is escalated so a person can verify the incident. A request that is already eligible and also mentions damage stays an approval: the policy already allows the unit, and the incident does not remove that eligibility.

Issuance for an employee under the max does not read `assigned_on`. A missing date on an older unit blocks only a replacement decision.

## Precedence

Evaluate in this order and stop at the first match:

1. `unknown_employee`
2. `unknown_role`
3. `vague_item`, `unlisted_item`, or `multiple_items`
4. `exception_language` when the request is not already eligible
5. `incomplete_equipment_record` when a replacement decision needs a missing date
6. `exceeds_role_maximum`
7. `refresh_not_elapsed`
8. Approve



## Canonical directory

Tools and tests use this directory. Tenure is stated as of 2026-09-30.


| ID     | Name         | Role                   | Hire date  | Equipment on file (`assigned_on`)                                             |
| ------ | ------------ | ---------------------- | ---------- | ----------------------------------------------------------------------------- |
| E-1001 | Alex Chen    | individual_contributor | 2022-01-15 | laptop 2022-02-01; monitor 2025-06-01; headset 2025-01-10                     |
| E-1002 | Jordan Patel | manager                | 2021-03-01 | laptop 2025-01-10; monitor 2023-01-15; docking_station 2024-06-01             |
| E-1003 | Sam Rivera   | individual_contributor | 2024-08-01 | laptop 2024-08-15; monitor 2024-08-15                                         |
| E-1004 | Riley Nguyen | manager                | 2020-06-01 | laptop 2023-05-01; monitor 2025-03-01; monitor 2025-03-01; headset 2024-11-01 |
| E-1005 | Casey Brooks | contractor             | 2025-11-01 | laptop 2025-11-15                                                             |
| E-1006 | Morgan Lee   | individual_contributor | 2019-04-01 | laptop 2021-04-01; monitor with no `assigned_on`                              |
| E-1007 | Taylor Kim   | director               | 2018-09-01 | laptop 2025-10-01; monitor 2024-01-01; monitor 2025-08-01; headset 2026-01-15 |




## Acceptance examples

These are the expected outcomes for the canonical directory. Dates are the assignment dates that drive the result.

### Clear approvals


| Employee | Request                                 | Basis                                                                                                                                                      |
| -------- | --------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| E-1001   | Replace the laptop. It is old and slow. | One laptop, assigned 2022-02-01. Individual-contributor refresh is 4 years (eligible 2026-02-01).                                                          |
| E-1002   | A second monitor for team reviews.      | Manager max is 2. One monitor is on file, so this is an issuance.                                                                                          |
| E-1004   | Refresh the laptop.                     | Manager refresh is 2 years. Laptop assigned 2023-05-01 (eligible 2025-05-01).                                                                              |
| E-1006   | Replace the laptop.                     | Laptop assigned 2021-04-01. Four-year refresh elapsed on 2025-04-01. The undated monitor is irrelevant.                                                    |
| E-1007   | Replace the older monitor.              | Director monitor refresh is 2 years. Oldest monitor assigned 2024-01-01 (eligible 2026-01-01). Two monitors are already on file, so this is a replacement. |




### Clear denials


| Employee | Request                            | Basis                                                                                                                   |
| -------- | ---------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| E-1003   | A new laptop. This one feels slow. | Laptop assigned 2024-08-15. Next eligible date is 2028-08-15. Reason `refresh_not_elapsed`.                             |
| E-1001   | A second monitor.                  | Individual-contributor max is 1 and one monitor is already on file. Reason `exceeds_role_maximum`.                      |
| E-1002   | Refresh the laptop.                | Laptop assigned 2025-01-10. Manager refresh is 2 years. Next eligible date is 2027-01-10. Reason `refresh_not_elapsed`. |
| E-1004   | A new headset.                     | One headset is on file, assigned 2024-11-01. Next eligible date is 2026-11-01. Reason `refresh_not_elapsed`.            |
| E-1007   | Another laptop for travel.         | Director max is 1 and the request asks for an additional laptop. Reason `exceeds_role_maximum`.                         |




### Escalations


| Employee | Request                                                        | Reason code                                                                                                   |
| -------- | -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| E-1003   | The laptop was ruined by a coffee spill and needs replacement. | `exception_language` (a refresh denial would otherwise apply; next eligible date would have been 2028-08-15). |
| E-1002   | A standing desk.                                               | `unlisted_item`                                                                                               |
| E-1001   | Something better for work.                                     | `vague_item`                                                                                                  |
| E-1001   | A new laptop and a headset.                                    | `multiple_items`                                                                                              |
| E-9999   | A headset.                                                     | `unknown_employee`                                                                                            |
| E-1005   | A laptop refresh.                                              | `unknown_role` (`contractor` has no policy row).                                                              |
| E-1006   | Replace the monitor.                                           | `incomplete_equipment_record`                                                                                 |




## What each tool must return

The server exposes four tools. Return values are plain structured data so tests can assert on them without an agent.

### `get_employee_info(employee_id)`

Returns `employee_id`, `name`, `role`, `hire_date`, `tenure` (years and months as of 2026-09-30), and `equipment` (list of `item` and `assigned_on`). An unknown id returns a not-found result and an empty equipment list.

### `get_policy_limits(role)`

Returns the four rows for that role: `item`, `max_on_file`, `refresh_years`. An unknown role returns a not-found result and no rows.

### `check_request_eligibility(employee_id, item)`

`item` is one catalog token. The function applies the eligibility rules and precedence that do not depend on free text. It returns:

- `status`: `eligible`, `ineligible`, or `undetermined`
- `reason_code`: `issuance_under_max`, `refresh_elapsed`, `refresh_not_elapsed`, `unknown_employee`, `unknown_role`, `unlisted_item`, or `incomplete_equipment_record`
- `role`, `units_on_file`, `max_on_file`, `oldest_assigned_on`, `refresh_years`, `next_eligible_date` when those values exist

`exceeds_role_maximum`, `vague_item`, `multiple_items`, and `exception_language` are decided from the request text by the agent, using this function's counts and dates as evidence. A quantity of 1 against a catalog item follows issuance and replacement as defined above.

### `flag_for_human_review(employee_id, request, reason)`

Appends one review record containing `employee_id`, the original request text, the reason code, and a timestamp. Each call creates a new record and returns a `review_id`. The call has a side effect and does not approve or deny the request.