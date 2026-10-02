Lab. Build an MCP server that exposes a mock claims system; build an agent that uses it to draft responses and escalate ambiguous cases.
Overview
This week you'll build a new system from scratch: an internal IT equipment request handler. You'll expose it as an MCP server, then build an agent that uses that server's tools to draft responses to requests, following the ReAct pattern, and escalate ambiguous cases rather than guessing. No starter files, datasets, or containers are provided.

The Scenario
Employees submit equipment requests (e.g., "I need a second monitor," "my laptop is 4 years old and slow, can I get a replacement"). Your system looks up the employee's role and equipment history, checks that role's policy limits, and either approves, denies, or escalates the request to a human reviewer if it's ambiguous.

If you're unsure how a tool or concept works beyond what the lesson covered, ask Claude (in a regular conversation, separate from your script) to explain it, or to help you research an unfamiliar library, technique, or error message before you implement it.

Suggested Approach (Read This Before Starting)
Don't try to build all four tools and a full agent at once. Build up in this order:

Install the MCP Python SDK (pip install mcp) and read through its quickstart documentation for building a server. Get the simplest possible example running first, a server with one trivial tool, and confirm you can start it and see it register that tool correctly, before writing any of your own business logic.
Build and test your first real tool in isolation. Write get_employee_info(employee_id) as a plain Python function first, with your mock employee data as a simple dictionary or JSON file. Write a unit test for it and get that passing before wrapping it as an MCP tool. Only after the plain function works and is tested should you decorate it as an MCP tool using the SDK's tool-registration pattern.
Confirm end-to-end connectivity with just that one tool. Write a small script that acts as an MCP client, connects to your running server, and calls get_employee_info. Confirm you get a real response back before adding anything else. This is your proof that the plumbing works.
Add the remaining three tools one at a time, following the same pattern: write and test the plain function first, then wrap it, then confirm it's callable through the client.
Only once all four tools work individually, build the agent. Start with a version that just makes one tool call based on a hardcoded request, confirm that works, then add the ReAct loop (letting the model decide which tool to call and whether it needs another one) on top of that working foundation.
Add reflection last, once the core approve/escalate logic is working end to end.
If you get stuck at any step, go back to the last thing that was confirmed working rather than continuing to build on top of something uncertain.

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
Rubric (100 points)
Criteria	Points
Requirements doc and policy rules are clear and specific enough to be testable	8
Minimal one-tool server/client connection confirmed working before full build	7
MCP server correctly implements all four tools	12
Unit tests cover normal and edge cases for each tool, and pass	13
Agent correctly connects to the MCP server and follows ReAct pattern	15
Agent correctly approves/denies clear-cut requests	10
Agent correctly escalates ambiguous requests instead of guessing, with clear reasons	15
Reflection step demonstrably improves or confirms at least one draft	10
Submitted and passing through the pipeline	10
Total	100
