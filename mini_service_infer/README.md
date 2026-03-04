# Policybot Pairing Mini-Service (CLI)
The HCPCS inference service can infer HCPCS codes relevant to a policy text using either keyword match- or LLM-based strategies.

## Run service
```bash
python main.py --input sample_input.json
```

## Scenario 1a
Currently the inference service always returns the top k inferred HCPCS codes. We’ve learned that this causes downstream errors. For instance, we are predicting HCPCS codes that are not actually relevant to the policy. Customers are searching for a policy using that HCPCS code and coming up with an irrelevant policy. What systems and logic changes could we implement to deal with these false positives?

## Scenario 1b
Currently the service can accept a single strategy (keyword match or llm) for inferring HCPCS codes. We would like to be able to pass multiple strategies and return the top codes between the strategies.
