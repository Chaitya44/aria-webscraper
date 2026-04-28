# Aria: Data Flow Diagram (DFD)

This diagram maps the flow of information from user input through the processing pipeline to the final structured output.

## Level 0: Context Diagram
```mermaid
graph LR
    User[User] -->|Input: URL/Query + Gemini Key| Aria[Aria System]
    Aria -->|Output: Structured JSON/CSV| User
```

## Level 1: Process Decomposition
```mermaid
graph TD
    User([User]) -->|1. Submit Request| FE[Next.js Frontend]
    FE -->|2. Authenticate Key| BE[FastAPI Backend]
    
    subgraph Core_Pipeline [Processing Pipeline]
        BE -->|3. Fetch Content| Scraper[Browser Scraper]
        Scraper -->|4. Raw HTML/MD| Gemini[Gemini AI Parser]
        Gemini -->|5. Structured Data| BE
    end
    
    BE -->|6. Log Entry| DB[(Firebase/Local DB)]
    BE -->|7. Send Results| FE
    FE -->|8. Render Data| User
```
