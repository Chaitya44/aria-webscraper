# Aria: Activity Diagram

Detailed workflow of a single scraping job from initiation to data structured logging.

```mermaid
activityDiagram
    start
    :User enters URL and Gemini Key;
    if (Key valid?) then (yes)
        :Initialize Scraping Engine;
        fork
            :Fetch Web Content (FastAPI);
            :Navigate Browser to URL;
            :Capture Clean Markdown/HTML;
        fork again
            :Monitor Connection Status;
            :Log Real-time Progress to UI;
        end fork
        :Invoke Gemini AI Parser;
        :Page Classification (Pass 1);
        :Data Structuring (Pass 2);
        if (Parsing successful?) then (yes)
            :Generate Structured JSON;
            :Save to History/Database;
            :Render Results in Dashboard;
        else (no)
            :Handle API/Model Error;
            :Display Error Message;
        endif
    else (no)
        :Reject Request;
        :Prompt for Valid Key;
    endif
    stop
```
