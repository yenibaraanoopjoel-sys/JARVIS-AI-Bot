# JARVIS AI Assistant

JARVIS is a personal AI assistant project targeting Windows desktop and PowerShell, with real conversational AI, voice input/output, opt-in facial and voice identity, persistent memory, and permission-controlled computer tools.

## Project status

This repository is being initialized from an empty repository. Capabilities are only described as implemented when code and tests verify that they work.

## Planned architecture

- Python core and command-line/PowerShell entry point
- Configurable AI provider (credentials supplied locally)
- Microphone speech-to-text and speaker text-to-speech
- Explicitly enrolled face/voice profiles with consent
- SQLite persistence for conversations, tasks, and profile metadata
- Permission-checked application, filesystem, and terminal tools
- Diagnostics, tests, logging, and clear failure reporting

## Security notes

- Copy `.env.example` to `.env` and provide your own credentials locally.
- Never commit `.env`, API keys, recordings, face images, embeddings, or personal database files.
- Face/voice matching is not sufficient by itself for sensitive actions; require explicit authorization.
- The camera and microphone must be opt-in, visibly active, and stoppable by the user.

## Setup

Setup instructions will be added alongside the implementation. Do not expect voice, model, camera, or automation features to work until their dependencies and required provider configuration have been installed and verified.
