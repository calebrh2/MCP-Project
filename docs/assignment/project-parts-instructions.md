What You'll Do
Part 1: Requirements and Design

Write a short requirements doc: what data does an equipment request need (employee, role, item requested, reason)? What are the policy rules (e.g., standard employees get one monitor every 3 years, managers get a laptop refresh every 2 years)? What counts as "ambiguous" and should be escalated rather than decided automatically? Define this yourself.

Part 2: Build the MCP Server

Following the Suggested Approach above, implement an MCP server exposing at least these tools:

get_employee_info(employee_id) — returns role, tenure, and current equipment on file
get_policy_limits(role) — returns what that role is eligible for and how often
check_request_eligibility(employee_id, item) — returns whether the request falls within policy
flag_for_human_review(employee_id, request, reason) — a side-effecting tool that escalates a request
Use mock/synthetic data for employees and policies, generated yourself.

Part 3: Test the Server in Isolation

Write unit tests for each tool's underlying function directly (not through the MCP protocol) before connecting anything to a live agent. Confirm correct behavior for both straightforward and edge cases (e.g., an employee ID that doesn't exist).

Part 4: Build the Agent (ReAct Pattern)

Build an agent that receives a natural-language equipment request, connects to your MCP server as a client, uses its tools to investigate the request, and follows an explicit ReAct-style trace (Thought → Action → Observation) to reach a decision. The agent should approve requests that clearly fall within policy, and escalate requests that are ambiguous or fall outside policy by calling flag_for_human_review, rather than guessing.

Part 5: Add Reflection

Before finalizing any drafted response, have the agent reflect on its own draft: does it accurately reflect what the policy tools returned? Does it avoid committing to something not confirmed by the data?

Part 6: Demonstrate Both Paths

Run your agent against at least 4 test requests: one clearly approved, one clearly denied, and at least two escalated for different reasons.

Part 7: Pipeline

Push your server code, agent code, and tests through your CI pipeline, with your unit tests running as part of it.

Deliverable
Submit a single PDF containing screenshots, in order, of:

Requirements doc and policy rules you defined
Terminal output confirming your minimal one-tool server and client connection worked (Suggested Approach step 3)
Your MCP server code (all four tools)
Your unit tests for each tool's underlying function, and terminal output showing them passing
Your agent code, including the MCP client connection
Full ReAct traces (Thought/Action/Observation) for all 4 test requests
The final decision/response for each of the 4 requests, including escalation reasons
Evidence of the reflection step catching or confirming at least one draft
A passing pipeline run