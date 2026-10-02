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