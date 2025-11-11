---
layout: default
title: "Cursor agent for Home Assistant"
---

# I just wanted to fix my heating, but built a Cursor agent for Home Assistant

After several weeks of working on AI systems that give vision to autonomous agents,  
I decided I needed a short break.

The options were:  
1. A few quiet days in Africa, or  
2. A weekend of building a DIY multi-zone heating system on top of Home Assistant.

Naturally, I didn't go to Africa.

---

Like most UK homes, mine had a gas boiler connected to a single wall thermostat.  
That meant one simple rule: if one room was cold, the system would heat the *entire* house.  
Sunny south-facing rooms would get hot and stuffy, while north-facing ones stayed chilly.  
And if one person liked sleeping in a cool bedroom while another preferred a warm living room — well, **welcome to the Bailey's paradox**: everyone's slightly unhappy.

Buying a fancy smart thermostat like Nest would've been the easiest path…  
but we're engineers — we don't do *easy*.

So I decided to build my own solution.

---

## The DIY approach

I wanted independent temperature control for each room, so I used **Home Assistant**, **Zigbee radiator valves**, and a **relay connected in parallel** with the existing thermostat — to keep the original system as a fallback.

Over a weekend, I went through five versions of the control logic.  
The first version was simple: each room had a target temperature;  
if any room dropped below its target, the boiler turned on,  
and valves in other rooms closed automatically to avoid overheating.

The latest version added:

- **Hysteresis**  
- **Predictive heating based on outdoor temperature**  
- **Thermal inertia compensation**

Now, the system turns off the boiler slightly before reaching the target,  
knowing the radiators will "coast" the room to the right temperature.  
This improved comfort *and* saved a noticeable amount of energy.

---

## From YAML pain to automation bliss

After the first version, though, I realized that **manual deployment was unbearable** —  
copying automations to the Home Assistant board, downloading logs, editing YAML files, and restarting services every time I changed a line.

Before starting the second version, I decided I couldn't take it anymore —  
and built tools to automate the entire process.

The system now consists of **two components**:

- **Home Assistant Agent** — runs directly on the Home Assistant board (I tested it on the Raspberry Pi version).  
  It can be installed right from the Home Assistant web interface and executes commands received from Cursor.  
- **MCP module for Cursor** — configured in Cursor's settings; it receives user commands and communicates with the Agent through Home Assistant's API.

Together, they let me edit, deploy, and restart automations directly from the IDE — without touching YAML files or the web UI.

I also added **version control integration**:  
every time a script or configuration file changes, it's committed to a local Git repository.  
That means I can safely roll back any change, experiment freely, and keep a full history of the system's evolution.

This completely changed my workflow.  
Instead of focusing on YAML syntax or remembering platform quirks,  
I could finally focus on *intent* — what the system should *do*.

For example:

- How should heating logic account for **external sensors**, since the built-in Zigbee valve sensor reads air near the radiator, not in the room?  
- How should the boiler react to changing **outdoor conditions**?  
- What's the most efficient **sequence of valve activations**?

All of this became easier to prototype, test, and refine — directly from the IDE.

---

## Results and what's next

The result was two components that completely solved my problem and **dramatically accelerated development, testing, and deployment** of my smart home setup.

They might be useful both for professional developers — who want to speed up Home Assistant scripting — and for non-technical users who simply want to bring their smart home ideas to life without digging through YAML files or command-line tools.

Along the way, I also added support for:

- Editing and deploying scripts directly from Cursor  
- Managing dashboards "as code"  
- Installing modules and HACS components without manually accessing the device  
- Keeping automation versions tracked in Git with instant rollback

Next steps: integrate CO and ventilation control, maybe even let the LLM suggest improved heating logic automatically.  
(And *maybe* go to Africa.)

---

## Repositories

Both components are open source:

- [home-assistant-cursor-agent](https://github.com/Coolver/home-assistant-cursor-agent) — the agent that runs on Home Assistant and executes commands from Cursor.  
- [home-assistant-mcp](https://github.com/Coolver/home-assistant-mcp) — the MCP integration for Cursor that communicates with the agent and provides an automation interface inside the IDE.

---

Thanks for reading — hope it inspires you to build your own "weekend project that got out of hand."
