# 🛩️ AI Airport Simulation - LLM Decision Making Playground

A sophisticated airport simulation designed specifically for **testing and comparing different Large Language Models (LLMs)** in complex, real-time air traffic control scenarios. This project serves as a controlled environment to evaluate how various AI systems handle safety-critical decision making, resource allocation, and emergency management in aviation operations.

## 🎯 Core Purpose: LLM Testing & Evaluation

**The primary goal of this simulation is to provide a standardized playground for comparing LLM performance in air traffic control decision making.** By presenting identical scenarios to different AI models, we can objectively evaluate:

- **Safety prioritization** (fuel emergencies, collision avoidance)
- **Resource optimization** (runway and gate assignments)
- **Crisis management** (multiple emergency scenarios)
- **Decision speed and consistency** under pressure
- **Learning from mistakes** (crash analysis and improvement)

### 🤖 Supported AI Systems

| AI Type | Implementation | Purpose |
|---------|---------------|---------|
| **Ollama** | Local LLMs (Llama3, Granite, CodeLlama, Mistral, etc.) | Primary testing platform |
| **OpenAI** | GPT-3.5/4 via API | Commercial LLM comparison |
| **Rule-Based** | Deterministic logic | Baseline performance benchmark |

## 🏆 Advanced Features

### ✈️ **Realistic Airport Operations**
- **11 aircraft states** with detailed lifecycle management
- **Dynamic fuel consumption** with realistic rates for each operation phase
- **Fuel refueling system** with time-dependent operations at gates
- **Multi-layered collision avoidance** (500px warning → 200px smart avoidance → 100px emergency → 10px crash)
- **Holding patterns** for both airborne (waiting to land) and ground (waiting for takeoff) aircraft
- **Emergency procedures** including go-around maneuvers and fuel emergency priority

### 🧠 **Intelligent Traffic Management**
- **Predictive collision detection** with automatic positioning to prevent cascade failures
- **Dynamic spawn rate adjustment** based on airport capacity and traffic density
- **Smart aircraft distribution** using sector-based spawning to prevent clustering
- **Traffic flow optimization** with real-time congestion monitoring
- **Emergency runway clearing** for critical fuel situations

### 📊 **Comprehensive Logging & Analysis**
- **Detailed AI decision logging** with reasoning, timing, and context
- **Crash analysis reports** with root cause identification
- **Performance metrics** including throughput, safety records, and efficiency
- **Fuel management tracking** with emergency detection and throttled warnings
- **Collision event analysis** with timeline reconstruction

### 🎮 **Advanced Simulation Engine**

#### **Modular Architecture**
```
🏗️ Simulation Components:
├── FlightScheduler    → Aircraft spawning and traffic management
├── CollisionSystem    → 4-layer collision prevention
├── FuelSystem        → Emergency detection and runway clearing
├── StateManager      → Aircraft lifecycle and transitions
└── SimulationEngine  → Coordination and main loop
```

#### **Sophisticated Aircraft Management**
- **Realistic fuel consumption** (takeoff: 30%, cruise: varies, landing: 10%, holding: 0.20%)
- **Intelligent refueling** (50-100% fuel targets with parallel boarding operations)
- **Emergency fuel handling** (critical <15%, low <25% with priority systems)
- **Collision avoidance behavior** with predictive positioning and safe separation

### ⚙️ **Configuration & Control**
- **YAML-based configuration** (`config.yaml`) for human-readable settings
- **Real-time AI switching** between different models during simulation
- **Configurable collision distances** and emergency thresholds
- **Dynamic spawn rates** and traffic density management
- **Comprehensive UI controls** with manual override capabilities

## 🚀 Quick Start

### Installation
```bash
# Clone and setup
git clone <repository-url>
cd ai-airport-simulation
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Basic Usage
```bash
# Run with graphics (default: Ollama AI, simulation stopped)
python main.py

# Run with graphics and auto-start simulation
python main.py --auto-start

# Compare different AI systems
python main.py --ai rule_based    # Baseline performance
python main.py --ai ollama        # Local LLM testing  
python main.py --ai openai        # Commercial LLM (requires API key)

# Auto-start with specific AI
python main.py --ai ollama --auto-start

# Headless performance testing
python main.py --headless --duration 300  # 5-minute test run
```

> **🆕 Recent Update**: Graphics mode now starts **stopped by default** for better user control. Use `--auto-start` to begin simulation immediately. AI switching buttons were removed from the UI - use the `--ai` command line flag instead.

### Ollama Setup (Recommended for LLM Testing)
```bash
# Install Ollama from https://ollama.ai/
# Pull models for testing
ollama pull llama3.1
ollama pull granite3.2
ollama pull codellama
ollama pull mistral

# List available models
ollama list
```

### OpenAI Setup
```bash
# Set your API key
export OPENAI_API_KEY="your-api-key-here"
```

## 📋 LLM Evaluation Framework

### Testing Scenarios
The simulation generates various scenarios to test LLM decision making:

1. **🔥 Fuel Emergencies**: Critical fuel aircraft requiring immediate landing
2. **💥 Collision Scenarios**: Multiple aircraft on collision courses
3. **🚁 Traffic Congestion**: High-density traffic requiring optimization
4. **⛽ Resource Management**: Runway and gate allocation under pressure
5. **🚨 Cascade Failures**: Multiple simultaneous emergencies

### Performance Metrics
```bash
# Example evaluation results
📊 LLM Performance Summary:
├── Safety Score: 95.2% (crashes avoided)
├── Efficiency: 87.3% (optimal resource usage)
├── Response Time: 2.1s average
├── Fuel Management: 98.1% (emergencies handled)
└── Decision Quality: 91.7% (expert evaluation)
```

### Comparing Models
```bash
# Run comparative tests
python benchmark_llms.py --models llama3.1,granite3.2,gpt-4 --duration 600
```

## 🛠️ Configuration

### config.yaml Structure
```yaml
simulation:
  max_aircraft: 15
  spawn_rate: 0.8
  ai_collision_interval: 0.25  # Faster response for emergencies
  
  collision:
    warning_distance: 500      # AI warning threshold
    smart_avoidance_distance: 200  # Automatic avoidance
    emergency_distance: 100    # Emergency separation
    crash_distance: 10         # Collision detection

airport:
  runways:
    count: 2
  gates:
    count: 4

ai:
  ollama_models: ["granite3.2:latest", "llama3.1:latest"]
  openai_model: "gpt-4"
  decision_logging: true
```

## 🎮 Controls & Interface

### Graphics Mode Controls
- **🚦 Start/Stop**: Control simulation state (simulation starts stopped by default)
- **👨‍✈️ Manual Mode**: Take direct control of aircraft
- **✈️ Add Aircraft**: Add test aircraft for testing
- **🔄 Reset Sim**: Reset the simulation
- **📊 Status Panels**: Real-time aircraft, runway, and system status

**Note**: AI selection is now done via command line (`--ai` flag). Use `--auto-start` to begin simulation immediately in graphics mode.

### Manual Control (when enabled)
- **Click aircraft** to select
- **L**: Assign landing runway
- **G**: Assign gate
- **T**: Assign takeoff
- **H**: Enter holding pattern

### Visual Status System
```
Aircraft Color Legend:
🟨 Approaching  🟠 Landing      🟡 Taxiing to Gate
🟢 At Gate     🔵 Boarding     🟣 Taxiing to Runway  
🔴 Taking Off  🟠 Holding     🔴 Crashed
```

## 📊 Analysis & Monitoring

### Real-Time Status Displays
- **Aircraft Status**: Position, fuel, assignments, state
- **Runway Queues**: Aircraft lineup for each runway
- **System Metrics**: Active aircraft, crashes, efficiency
- **Selected Aircraft**: Detailed status of chosen aircraft

### Log Analysis
```bash
# View AI decisions
tail -f logs/ai_decisions_YYYYMMDD_HHMMSS.log

# Analyze crashes
grep "CRASH" logs/ai_decisions_*.log

# Performance metrics
grep "PERFORMANCE" logs/ai_decisions_*.log
```

## 🔬 Research Applications

### Academic Research
- **LLM safety evaluation** in critical decision scenarios
- **Multi-agent coordination** studies
- **Real-time AI performance** under pressure
- **Human-AI interaction** in safety-critical systems

### Industry Applications
- **AI model validation** for aviation systems
- **Training data generation** for air traffic control AI
- **Comparative analysis** of commercial vs open-source LLMs
- **Safety protocol testing** and validation

## 🛡️ Safety & Testing Features

### Collision Prevention System
1. **Early Warning** (500px): AI receives collision alerts
2. **Smart Avoidance** (200px): Automatic intelligent positioning  
3. **Emergency Separation** (100px): Immediate automatic separation
4. **Crash Detection** (10px): Final collision detection

### Fuel Management
- **Real-time monitoring** with emergency detection
- **Priority systems** for critical fuel aircraft
- **Realistic consumption** rates for all operation phases
- **Refueling simulation** with time-dependent operations

### Emergency Procedures
- **Go-around maneuvers** for safety
- **Emergency runway clearing** for critical aircraft
- **Holding pattern management** with fuel safety checks
- **Automatic crash prevention** systems

## 🏗️ Architecture Details

### Modular Design
```python
# Core system components
SimulationEngine
├── FlightScheduler     # Traffic generation and flow
├── CollisionSystem     # Multi-layer collision prevention  
├── FuelSystem         # Emergency detection and management
├── StateManager       # Aircraft lifecycle management
└── AIManager          # LLM integration and switching
```

### AI Integration
```python
# AI interface for LLM testing
class BaseAI:
    def make_atc_decision(self, aircraft, airport_state):
        # LLM receives full context
        # Returns structured decision with reasoning
        pass
```

## 🖥️ Command Line Options

### Core Options
```bash
# Basic simulation modes
python main.py                          # Graphics mode, stopped by default
python main.py --auto-start             # Graphics mode, auto-start simulation
python main.py --headless               # Headless mode, no graphics
python main.py --headless --duration 60 # Headless for 60 seconds (headless only)

# AI selection (choose before starting)
python main.py --ai rule_based          # Use rule-based AI
python main.py --ai ollama              # Use Ollama (local LLM)
python main.py --ai openai              # Use OpenAI (API/local server)
python main.py --ai remote              # Use remote AI endpoint (legacy)

# Configuration
python main.py --config                 # Create default config file
python main.py --runways 3              # Override runway count
python main.py --gates 6                # Override gate count
python main.py --ollama-model llama3.1  # Override Ollama model

# Combined examples
python main.py --ai ollama --auto-start             # Auto-start with Ollama
python main.py --ai openai --auto-start --gates 8   # OpenAI with custom gates
```

### Help & Usage
```bash
python main.py --help    # Show all available options
```

## 🤝 Contributing

### Adding New LLMs
1. Extend `BaseAI` class
2. Implement decision logic
3. Add to AI manager
4. Update configuration

### Testing Scenarios
1. Add scenario generators
2. Define evaluation metrics  
3. Create benchmark tests
4. Document expected behaviors

## 📈 Future Enhancements

- **🌩️ Weather systems** affecting AI decisions
- **🏢 Multi-airport scenarios** for complex coordination
- **📱 Web interface** for remote LLM testing
- **📊 Advanced analytics** dashboard
- **🎓 Training mode** for LLM fine-tuning
- **🔄 Replay system** for scenario analysis

## 📄 License

Open source project for research and educational purposes. See LICENSE file for details.

---

**🎯 Ready to test your LLM's air traffic control skills?** Start the simulation and see how different AI models handle the pressure of managing airport operations! 

For questions about LLM integration or performance comparisons, please open an issue or contribute to the project. 