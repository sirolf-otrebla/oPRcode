---
confirmed: true
---
## 0. Context
The sample service maps request IDs to stored records.
## 1. Why
The change rejects missing records consistently.
## 2. What
The lookup now returns an explicit not-found result.
## 3. How
The handler checks the lookup result before formatting the response.
## Additional Context
None.
## Focus
Error behavior.
## Exclusions
None.
## Operational Assumptions
Request IDs are untrusted strings.
