# Validation Test Plan

This document describes test scenarios for the validation system (Tool Output Traceability + Voice/Text Consistency).

## Test Environment Setup

Before running tests:
1. Ensure RAG knowledge base is populated: `cd rag && python example.py`
2. Start agent: `adk run banking_agent` or `adk web .`
3. Monitor logs for validation feedback and retry attempts

## Test Cases

### Test Case 1: Successful Validation (First Attempt)
**Objective:** Verify response passes validation on first try

**Input:** "What is the Global Innovation Index?"

**Expected Behavior:**
- Concierge agent calls search_documents()
- Generates grounded response about GII
- Validator agent validates successfully
- Loop exits after 1 iteration (escalate=True)
- User sees normal response

**Validation Checks:**
- `temp:retry_count` remains 0
- No validation feedback in logs
- Response grounded in RAG output
- Voice and text semantically consistent

---

### Test Case 2: Validation Retry - Passes on Second Attempt
**Objective:** Verify retry mechanism with feedback injection

**Input:** Ask a question that might initially produce inconsistent voice/text

**Expected Behavior:**
- Iteration 1: Validator detects issue, sets escalate=False
- Validator stores `temp:validation_feedback` with specific issues
- Iteration 2: Concierge sees feedback in instruction template
- Concierge generates improved response
- Validator validates successfully, sets escalate=True
- User sees corrected response

**Validation Checks:**
- `temp:retry_count` increments to 1
- Validation feedback present in logs
- Second attempt addresses feedback
- Final response passes all checks

---

### Test Case 3: Max Retries - Fallback Message
**Objective:** Verify fallback handler after 3 failed attempts

**Setup:** Temporarily modify VALIDATOR_INSTRUCTIONS to be very strict

**Expected Behavior:**
- Iterations 1-3: Validator rejects all attempts
- After iteration 3: `handle_validation_failure` callback triggers
- User receives fallback message:
  - voice_str: "I need to connect you with a specialist for this question."
  - text: "I apologize, but I need to escalate your question..."
  - send_to_ui: True

**Validation Checks:**
- `temp:retry_count` reaches 2 (3 total attempts: 0, 1, 2)
- Error logged: "Validation failed after 3 attempts"
- Fallback message returned to user
- No stack traces or errors visible to user

---

### Test Case 4: RAG Returns No Results
**Objective:** Verify proper handling when RAG finds nothing

**Input:** "Tell me about quantum computing in the GII"

**Expected Behavior:**
- search_documents() returns "No information found..."
- Concierge generates response acknowledging no info
- Validator validates that response properly acknowledges lack of data
- Validator sets escalate=True (valid response for "no results")

**Validation Checks:**
- Response doesn't fabricate information
- Response explicitly states info not available
- Voice/text both acknowledge lack of data
- Traceability check passes (grounded in "no results" output)

---

### Test Case 5: Voice/Text Inconsistency Detection
**Objective:** Verify consistency_check catches mismatched fields

**Scenario:** Manually test with agent that produces:
- voice_str: "Innovation rankings show Switzerland leads."
- text: "# Tax Policy\n\nTax advantages in Luxembourg..."

**Expected Behavior:**
- Validator detects topic mismatch
- consistency_check = False
- Specific feedback: "text discusses tax policy while voice discusses innovation rankings - different topics"
- Retry with feedback

**Validation Checks:**
- consistency_check = False
- Feedback mentions specific topic mismatch
- Retry attempts to align topics

---

### Test Case 6: Hallucination Detection (Traceability)
**Objective:** Verify traceability_check catches fabricated data

**Scenario:** Response includes data not in RAG output:
- RAG: "Switzerland ranks #1 in innovation"
- Response voice_str: "Switzerland leads with score of 87.5"

**Expected Behavior:**
- Validator detects fabricated score "87.5"
- traceability_check = False
- Specific feedback: "voice_str mentions score 87.5 but this number doesn't appear in RAG output"
- Retry without fabricated numbers

**Validation Checks:**
- traceability_check = False
- Feedback identifies specific fabricated fact
- Retry removes hallucinated data

---

### Test Case 7: Grounded Follow-up Questions
**Objective:** Verify follow-up questions are also validated

**Scenario:** Response includes follow-up about topic not in RAG

**Expected Behavior:**
- Validator checks follow_up_questions against RAG output
- Flags ungrounded follow-ups in feedback
- Retry removes or replaces with grounded questions

**Validation Checks:**
- Feedback mentions follow-up question issue
- Final response has RAG-grounded follow-ups only

---

### Test Case 8: Greeting (No Validation Needed)
**Objective:** Verify validation works for non-RAG responses

**Input:** "Hello"

**Expected Behavior:**
- Concierge generates greeting (no RAG call)
- temp:last_rag_output may be empty or from previous turn
- Validator handles greeting appropriately
- May pass or require special handling

**Validation Checks:**
- System doesn't crash on greeting
- Appropriate response returned
- No unnecessary validation errors

---

### Test Case 9: Complex Multi-Document Query
**Objective:** Verify validation with rich RAG results

**Input:** "What are the top 3 innovation leaders and their strengths?"

**Expected Behavior:**
- RAG returns multiple results about top countries
- Concierge synthesizes information
- Validator ensures all claims traceable to RAG results
- All country names, rankings, strengths must be in RAG output

**Validation Checks:**
- Response covers multiple aspects from RAG
- No invented rankings or data
- Voice summarizes, text elaborates consistently

---

### Test Case 10: State Persistence Across Loop
**Objective:** Verify temp state persists through retry loop

**Expected Behavior:**
- Iteration 1: Sets temp:last_rag_output, temp:retry_count=0
- Iteration 2: Same temp:last_rag_output available, temp:retry_count=1
- Iteration 3: State still available, temp:retry_count=2

**Validation Checks:**
- temp:last_rag_output doesn't get cleared between iterations
- temp:retry_count increments correctly
- temp:validation_feedback persists for concierge to read

---

## Manual Testing Commands

### Run Interactive Agent
```bash
cd /home/ketan/learning/adk-learning
adk run banking_agent
```

### Run with Web UI
```bash
cd /home/ketan/learning/adk-learning
adk web .
```

### Run Specific Eval Case (Future)
```bash
adk eval banking_agent banking_agent/test_suite.evalset.json:test_case_validation_retry
```

---

## Expected Metrics

### Success Criteria:
- Test Cases 1-4: Must pass
- Test Cases 5-7: Must detect and retry
- Test Case 8: Must handle gracefully
- Test Cases 9-10: Must pass

### Performance Expectations:
- Valid response (1 iteration): 4-7 seconds
- Retry once (2 iterations): 8-14 seconds
- Max retries (3 iterations): 12-21 seconds
- Fallback: Returns immediately after iteration 3

### Compliance Checks:
- All validation failures logged
- No user-visible errors
- Fallback message professional
- Audit trail complete (logs contain feedback)

---

## Troubleshooting

### Issue: Validation always fails
- Check VALIDATOR_INSTRUCTIONS not too strict
- Verify temp state keys correct (temp:last_rag_output, avery_response)
- Check template variable syntax in prompts

### Issue: Retry feedback not visible
- Check concierge agent reads temp:validation_feedback
- Verify template syntax: `{% if temp:retry_count > 0 %}`
- Check ADK template variable substitution working

### Issue: Loop doesn't exit
- Verify validator returns escalate=True when valid
- Check ValidationResult schema matches
- Verify LoopAgent checks escalate flag

### Issue: Fallback never triggers
- Check max_iterations=3 on LoopAgent
- Verify after_agent_callback attached
- Check callback reads temp:is_valid correctly

---

## Adding Automated Tests

To create proper evalset.json test cases:

1. Run agent interactively with test scenario
2. Capture conversation using `--save_session`
3. Extract relevant parts for evalset.json
4. Add to test_suite.evalset.json

Or use ADK eval framework to generate test cases programmatically.
