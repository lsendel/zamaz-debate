# Gemini's Context and Memory

This file serves as the primary, persistent context store for the Gemini assistant. It helps maintain a shared understanding of the project's state, goals, and history across multiple sessions.

## Core Strategy

The strategy for maintaining context is multi-layered:

1.  **Working Memory (`GEMINI_CONTEXT.md`):** This file is the single source of truth for key decisions, architectural summaries, and session-to-session continuity. Gemini will read this at the start of each session and append summaries at the end.
2.  **Reference Library (Project Docs):** Existing documentation (`README.md`, files in `docs/`, etc.) will be consulted for established patterns and plans.
3.  **Active Search (On-Demand RAG):** For specific queries, Gemini will use its search and read tools to get real-time, accurate information from the codebase.
4.  **Personal Preferences (`save_memory` tool):** The `save_memory` tool will be used for user-specific preferences that apply globally, not just to this project.

## How to Use

-   **Gemini:** Read this file at the start of every session. Append summaries of significant changes or decisions.
-   **User:** If Gemini seems to be missing context, refer it back to this file. Feel free to add notes or clarifications here directly.
