sequenceDiagram
    participant User
    participant root_agent as SequentialAgent
    participant intent_agent as LlmAgent
    participant concierge_with_validation as LoopAgent
    participant concierge_agent as LlmAgent (Avery)
    participant search_documents as RAG Tool
    participant validator_agent as LlmAgent
    participant handle_validation_failure as Fallback Handler

    User->>root_agent: Sends a message
    root_agent->>intent_agent: Classify intent
    intent_agent-->>root_agent: Returns intent
    root_agent->>concierge_with_validation: Process message
    
    loop 3 times on validation failure
        concierge_with_validation->>concierge_agent: Generate response
        concierge_agent->>search_documents: Search knowledge base
        search_documents-->>concierge_agent: Returns search results
        concierge_agent-->>concierge_with_validation: Returns response
        
        concierge_with_validation->>validator_agent: Validate response
        alt Response is valid
            validator_agent-->>concierge_with_validation: Returns validation success
            concierge_with_validation-->>root_agent: Returns final response
        else Response is invalid
            validator_agent-->>concierge_with_validation: Returns validation failure and feedback
        end
    end
    
    alt Validation fails after 3 retries
        concierge_with_validation->>handle_validation_failure: Trigger fallback
        handle_validation_failure-->>root_agent: Returns escalation message
    end

    root_agent-->>User: Sends final response or escalation