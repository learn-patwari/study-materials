# SprintForge Desktop Mascot Asset Pack

This pack is structured for a Windows desktop mascot that lives in a transparent,
frameless, draggable, always-on-top window.

## Core states
- idle
- greeting
- thinking
- idea
- working
- explaining
- ready
- success
- celebrating

## Animation formats
`animations/*.webp` is recommended for modern desktop rendering because it
supports animation and alpha transparency. GIF files are provided as fallback.

## Runtime behavior
Use `mascot_state_machine.json` as the state/event contract.

Example:
`agent_started -> working`
`task_complete -> celebrating`
`return_to_waiting -> idle`

## UI assets
- chatbot_profile.png
- windows_taskbar.png
- system_tray.png
- application_exe.png

## Recommended desktop window
Transparent + frameless + always-on-top + draggable + system-tray controlled.
