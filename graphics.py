"""
Graphics and visualization system using pygame.
"""
import pygame
import math
from typing import Dict, Tuple
from models import AircraftState
from models.airport import RunwayState
from config import get_config

# Color definitions
COLORS = {
    'background': (50, 50, 50),
    'runway': (100, 100, 100),
    'runway_lines': (255, 255, 255),
    'gate': (150, 150, 150),
    'gate_occupied': (255, 100, 100),
    'aircraft_approaching': (0, 255, 0),
    'aircraft_landing': (255, 255, 0),
    'aircraft_go_around': (255, 128, 0),    # Orange for go-around
    'aircraft_taxiing': (0, 150, 255),
    'aircraft_at_gate': (255, 150, 0),
    'aircraft_boarding': (255, 100, 150),
    'aircraft_departing': (255, 0, 255),
    'text': (255, 255, 255),
    'ui_panel': (40, 40, 40),
    'button': (80, 80, 80),
    'button_hover': (120, 120, 120),
    'selected': (255, 255, 100)
}

class Button:
    """Simple button UI element."""
    
    def __init__(self, x: int, y: int, width: int, height: int, text: str, callback=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.callback = callback
        self.hovered = False
        self.font = pygame.font.Font(None, 24)
    
    def handle_event(self, event):
        """Handle mouse events."""
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.hovered and self.callback:
                self.callback()
    
    def draw(self, screen):
        """Draw the button."""
        color = COLORS['button_hover'] if self.hovered else COLORS['button']
        pygame.draw.rect(screen, color, self.rect)
        pygame.draw.rect(screen, COLORS['text'], self.rect, 2)
        
        text_surface = self.font.render(self.text, True, COLORS['text'])
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)

class AirportRenderer:
    """Handles rendering of the airport simulation."""
    
    def __init__(self, simulation_engine):
        pygame.init()
        self.simulation = simulation_engine
        self.airport = simulation_engine.airport
        
        # Setup display with more space for improved UI
        config = get_config()
        self.screen_width = config.airport.airport_width + 350  # More space for UI
        self.screen_height = config.airport.airport_height
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Airport Control Tower Simulation")
        
        # Fonts
        self.font_small = pygame.font.Font(None, 18)
        self.font_medium = pygame.font.Font(None, 24)
        self.font_large = pygame.font.Font(None, 32)
        
        # UI elements
        self.selected_aircraft = None
        self.buttons = []
        self.setup_ui()
        
        # Clock for FPS control
        self.clock = pygame.time.Clock()
        self.running = True
    
    def setup_ui(self):
        """Setup UI buttons and panels."""
        config = get_config()
        ui_x = config.airport.airport_width + 20
        button_width = 120  # Width for button text
        button_height = 35
        button_spacing_y = 45
        button_spacing_x = 130  # Horizontal spacing for buttons
        
        # Control buttons arranged in two columns at the top
        self.buttons = [
            # Top row - Primary controls
            Button(ui_x, 70, button_width, button_height, "Start / Stop", self.toggle_simulation),
            Button(ui_x + button_spacing_x, 70, button_width, button_height, "Manual Mode", self.toggle_manual_mode),
            
            # Second row - Simulation controls
            Button(ui_x, 70 + button_spacing_y, button_width, button_height, "Add Aircraft", self.add_test_aircraft),
            Button(ui_x + button_spacing_x, 70 + button_spacing_y, button_width, button_height, "Reset Sim", self.reset_simulation),
        ]
    
    def toggle_simulation(self):
        """Toggle simulation running state."""
        if self.simulation.running:
            self.simulation.stop()
        else:
            self.simulation.start()
    
    def toggle_manual_mode(self):
        """Toggle manual control mode."""
        self.simulation.manual_mode = not self.simulation.manual_mode
    

    
    def add_test_aircraft(self):
        """Add a test aircraft for testing."""
        from models import Aircraft, Position, AircraftState
        import random
        import math
        
        config = get_config()
        
        # 70% chance to spawn as arrival, 30% chance to spawn at gate
        spawn_at_gate = random.random() < 0.3
        
        aircraft = Aircraft(
            callsign=f"TEST{random.randint(100, 999)}"
        )
        
        if spawn_at_gate:
            # Try to spawn at an available gate
            available_gate = self.airport.get_available_gate()
            if available_gate:
                aircraft.position = Position(available_gate.position.x, available_gate.position.y)
                aircraft.target_position = Position(available_gate.position.x, available_gate.position.y)
                aircraft.state = AircraftState.AT_GATE
                aircraft.assigned_gate = available_gate.id
                aircraft.fuel = 100.0  # Full fuel for departing aircraft
                available_gate.occupied_by = aircraft.id
                print(f"SPAWN: {aircraft.callsign} spawned at gate {available_gate.id}")
            else:
                # No gates available, spawn as arrival instead
                spawn_at_gate = False
        
        if not spawn_at_gate:
            # Spawn as arrival aircraft at random edge with proper separation
            spawn_methods = ['circle', 'edge']
            spawn_method = random.choice(spawn_methods)
            
            if spawn_method == 'circle':
                # Spawn around a circle at safe distance from airport center
                angle = random.uniform(0, 2 * math.pi)
                spawn_distance = random.uniform(300, 500)  # Vary distance for more spread
                center_x = config.airport.airport_width / 2
                center_y = config.airport.airport_height / 2
                spawn_x = center_x + math.cos(angle) * spawn_distance
                spawn_y = center_y + math.sin(angle) * spawn_distance
            else:
                # Spawn at random edge positions with better distribution
                edge = random.choice(['top', 'bottom', 'left', 'right'])
                margin = 100  # Stay away from exact corners
                
                if edge == 'top':
                    spawn_x = random.randint(margin, config.airport.airport_width - margin)
                    spawn_y = random.randint(0, 50)  # Near top edge
                elif edge == 'bottom':
                    spawn_x = random.randint(margin, config.airport.airport_width - margin)
                    spawn_y = random.randint(config.airport.airport_height - 50, config.airport.airport_height)
                elif edge == 'left':
                    spawn_x = random.randint(0, 50)  # Near left edge
                    spawn_y = random.randint(margin, config.airport.airport_height - margin)
                else:  # right
                    spawn_x = random.randint(config.airport.airport_width - 50, config.airport.airport_width)
                    spawn_y = random.randint(margin, config.airport.airport_height - margin)
            
            # Ensure aircraft stay within screen bounds
            margin = 30
            spawn_x = max(margin, min(config.airport.airport_width - margin, spawn_x))
            spawn_y = max(margin, min(config.airport.airport_height - margin, spawn_y))
            
            aircraft.position = Position(spawn_x, spawn_y)
            aircraft.state = AircraftState.APPROACHING
            # Set realistic fuel level for arriving aircraft (10-12%)
            aircraft.fuel = random.uniform(10.0, 12.0)
            # Set target to airport center for testing
            aircraft.target_position = Position(
                config.airport.airport_width // 2,
            config.airport.airport_height // 2
        )
        self.airport.add_aircraft(aircraft)
    
    def reset_simulation(self):
        """Reset the simulation."""
        self.simulation.stop()
        self.airport.aircraft.clear()
        for runway in self.airport.runways:
            runway.state = RunwayState.AVAILABLE
            runway.occupied_by = None
        for gate in self.airport.gates:
            gate.occupied_by = None
        self.selected_aircraft = None
    

    def handle_events(self):
        """Handle pygame events."""
        config = get_config()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return False
            
            # Handle UI button events
            for button in self.buttons:
                button.handle_event(event)
            
            # Handle aircraft selection
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.pos[0] < config.airport.airport_width:  # Only in simulation area
                    self.selected_aircraft = self.get_aircraft_at_position(event.pos)
            
            # Handle manual control commands
            if event.type == pygame.KEYDOWN and self.simulation.manual_mode and self.selected_aircraft:
                self.handle_manual_commands(event.key)
            
            # Handle model switching (M key + number keys for ollama models)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_m:
                models = getattr(self.simulation, 'ai_manager', None)
                if models:
                    available_models = models.get_ollama_models()
                    if available_models:
                        print(f"Press 1-{len(available_models)} to switch ollama models:")
                        for i, model in enumerate(available_models[:9]):  # Limit to 9 models
                            print(f"  {i+1}: {model}")
            
            # Handle model selection (number keys 1-9)
            if event.type == pygame.KEYDOWN and pygame.K_1 <= event.key <= pygame.K_9:
                if hasattr(self.simulation, 'ai_manager'):
                    models = self.simulation.ai_manager.get_ollama_models()
                    model_index = event.key - pygame.K_1
                    if 0 <= model_index < len(models):
                        self.simulation.ai_manager.switch_ollama_model(models[model_index])
        
        return True
    
    def get_aircraft_at_position(self, pos: Tuple[int, int]):
        """Get aircraft at mouse position."""
        for aircraft in self.airport.aircraft:
            aircraft_pos = (aircraft.position.x, aircraft.position.y)
            distance = math.sqrt((pos[0] - aircraft_pos[0])**2 + (pos[1] - aircraft_pos[1])**2)
            if distance < 20:  # 20 pixel selection radius
                return aircraft.id
        return None
    
    def handle_manual_commands(self, key):
        """Handle manual control commands via keyboard."""
        aircraft = self.airport.get_aircraft(self.selected_aircraft)
        if not aircraft:
            return
        
        command = None
        
        if key == pygame.K_l:  # Land command
            runway = self.airport.get_available_runway()
            if runway:
                command = {
                    'aircraft_id': aircraft.id,
                    'action': 'assign_landing',
                    'target': runway.id
                }
        
        elif key == pygame.K_g:  # Gate command
            gate = self.airport.get_available_gate()
            if gate:
                command = {
                    'aircraft_id': aircraft.id,
                    'action': 'assign_gate',
                    'target': gate.id
                }
        
        elif key == pygame.K_t:  # Takeoff command
            runway = self.airport.get_available_runway()
            if runway:
                command = {
                    'aircraft_id': aircraft.id,
                    'action': 'assign_takeoff',
                    'target': runway.id
                }
        
        elif key == pygame.K_h:  # Hold pattern
            command = {
                'aircraft_id': aircraft.id,
                'action': 'hold_pattern'
            }
        
        if command:
            self.simulation.add_manual_command(command)
    
    def draw_runway(self, runway):
        """Draw a runway."""
        start = (runway.start_position.x, runway.start_position.y)
        end = (runway.end_position.x, runway.end_position.y)
        
        # Draw runway surface
        pygame.draw.line(self.screen, COLORS['runway'], start, end, int(runway.width))
        
        # Draw runway markings
        pygame.draw.line(self.screen, COLORS['runway_lines'], start, end, 2)
        
        # Draw runway number
        center_x = (start[0] + end[0]) // 2
        center_y = (start[1] + end[1]) // 2
        text = self.font_small.render(f"RW{runway.id}", True, COLORS['text'])
        self.screen.blit(text, (center_x - 15, center_y - 20))
        
        # Draw status indicator
        status_color = COLORS['gate_occupied'] if runway.state != RunwayState.AVAILABLE else COLORS['gate']
        pygame.draw.circle(self.screen, status_color, (center_x, center_y + 15), 5)
    
    def draw_gate(self, gate):
        """Draw a gate."""
        pos = (int(gate.position.x), int(gate.position.y))
        color = COLORS['gate_occupied'] if not gate.is_available else COLORS['gate']
        
        # Draw gate as rectangle
        rect = pygame.Rect(pos[0] - 15, pos[1] - 10, 30, 20)
        pygame.draw.rect(self.screen, color, rect)
        pygame.draw.rect(self.screen, COLORS['text'], rect, 1)
        
        # Draw gate number
        text = self.font_small.render(f"G{gate.id}", True, COLORS['text'])
        self.screen.blit(text, (pos[0] - 8, pos[1] - 5))
    
    def get_aircraft_color(self, aircraft):
        """Get color for aircraft based on state."""
        state_colors = {
            AircraftState.APPROACHING: COLORS['aircraft_approaching'],
            AircraftState.HOLDING: (255, 165, 0),  # Orange for holding pattern
            AircraftState.LANDING: COLORS['aircraft_landing'],
            AircraftState.GO_AROUND: COLORS['aircraft_go_around'],
            AircraftState.TAXIING_TO_GATE: COLORS['aircraft_taxiing'],
            AircraftState.AT_GATE: COLORS['aircraft_at_gate'],
            AircraftState.BOARDING_DEBOARDING: COLORS['aircraft_boarding'],
            AircraftState.TAXIING_TO_RUNWAY: COLORS['aircraft_taxiing'],
            AircraftState.TAKING_OFF: COLORS['aircraft_departing'],
            AircraftState.CRASHED: (255, 0, 0)  # Red for crashed aircraft
        }
        return state_colors.get(aircraft.state, COLORS['aircraft_approaching'])
    
    def draw_aircraft(self, aircraft):
        """Draw an aircraft."""
        pos = (int(aircraft.position.x), int(aircraft.position.y))
        color = self.get_aircraft_color(aircraft)
        
        # Highlight selected aircraft
        if self.selected_aircraft == aircraft.id:
            pygame.draw.circle(self.screen, COLORS['selected'], pos, 18, 3)
        
        # Draw aircraft shape based on state
        if aircraft.state.value == "crashed":
            # Draw crashed aircraft as red X
            crash_size = 15
            pygame.draw.line(self.screen, (255, 0, 0), 
                           (pos[0] - crash_size, pos[1] - crash_size), 
                           (pos[0] + crash_size, pos[1] + crash_size), 4)
            pygame.draw.line(self.screen, (255, 0, 0), 
                           (pos[0] + crash_size, pos[1] - crash_size), 
                           (pos[0] - crash_size, pos[1] + crash_size), 4)
            # Draw explosion effect
            pygame.draw.circle(self.screen, (255, 100, 0), pos, 20, 2)
        elif aircraft.target_position:
            # Calculate angle to target
            dx = aircraft.target_position.x - aircraft.position.x
            dy = aircraft.target_position.y - aircraft.position.y
            angle = math.atan2(dy, dx)
            
            # Triangle points
            size = 12
            points = [
                (pos[0] + size * math.cos(angle), pos[1] + size * math.sin(angle)),
                (pos[0] + size * math.cos(angle + 2.6), pos[1] + size * math.sin(angle + 2.6)),
                (pos[0] + size * math.cos(angle - 2.6), pos[1] + size * math.sin(angle - 2.6))
            ]
            pygame.draw.polygon(self.screen, color, points)
        else:
            pygame.draw.circle(self.screen, color, pos, 8)
        
        # Draw fuel bar (only for non-crashed aircraft)
        if aircraft.state.value != "crashed":
            fuel_bar_width = 30
            fuel_bar_height = 4
            fuel_bar_x = pos[0] - fuel_bar_width // 2
            fuel_bar_y = pos[1] - 20
            
            # Background bar
            pygame.draw.rect(self.screen, (50, 50, 50), 
                           (fuel_bar_x, fuel_bar_y, fuel_bar_width, fuel_bar_height))
            
            # Fuel level bar
            fuel_width = int((aircraft.fuel / 100.0) * fuel_bar_width)
            if aircraft.fuel > 25:
                fuel_color = (0, 255, 0)  # Green
            elif aircraft.fuel > 10:
                fuel_color = (255, 255, 0)  # Yellow
            else:
                fuel_color = (255, 0, 0)  # Red
            
            if fuel_width > 0:
                pygame.draw.rect(self.screen, fuel_color, 
                               (fuel_bar_x, fuel_bar_y, fuel_width, fuel_bar_height))
        
        # Draw callsign
        text_color = (255, 0, 0) if aircraft.state.value == "crashed" else COLORS['text']
        text = self.font_small.render(aircraft.callsign, True, text_color)
        self.screen.blit(text, (pos[0] + 15, pos[1] - 10))
        
        # Draw fuel percentage for critical aircraft
        if aircraft.state.value != "crashed" and hasattr(aircraft, 'is_critical_fuel') and aircraft.is_critical_fuel():
            fuel_text = self.font_small.render(f"{aircraft.fuel:.0f}%", True, (255, 0, 0))
            self.screen.blit(fuel_text, (pos[0] + 15, pos[1] + 5))
        
        # Draw target line if in manual mode
        if (self.simulation.manual_mode and aircraft.target_position and 
            self.selected_aircraft == aircraft.id and aircraft.state.value != "crashed"):
            target_pos = (int(aircraft.target_position.x), int(aircraft.target_position.y))
            pygame.draw.line(self.screen, COLORS['selected'], pos, target_pos, 2)
    
    def draw_hold_stop_area(self):
        """Draw graphical hold/stop area for aircraft."""
        config = get_config()
        # Define hold area position (bottom right of simulation area)
        hold_area_width = 220  # Increased to accommodate wider spacing
        hold_area_height = 140  # Increased to accommodate taller spacing
        hold_area_x = config.airport.airport_width - hold_area_width - 20
        hold_area_y = config.airport.airport_height - hold_area_height - 20
        
        # Draw hold area background
        hold_rect = pygame.Rect(hold_area_x, hold_area_y, hold_area_width, hold_area_height)
        pygame.draw.rect(self.screen, (60, 60, 60), hold_rect)  # Dark gray background
        pygame.draw.rect(self.screen, COLORS['text'], hold_rect, 2)  # White border
        
        # Draw title
        title_text = self.font_medium.render("HOLD/STOP AREA", True, COLORS['text'])
        title_rect = title_text.get_rect()
        title_x = hold_area_x + (hold_area_width - title_rect.width) // 2
        self.screen.blit(title_text, (title_x, hold_area_y + 5))
        
        # Find aircraft that should be shown in hold area
        holding_aircraft = [a for a in self.airport.aircraft 
                           if a.state.value in ['at_gate', 'taxiing_to_gate'] or 
                              (a.state.value == 'approaching' and a.assigned_runway is None)]
        
        # Separate by type for organization
        gate_aircraft = [a for a in holding_aircraft if a.state.value == 'at_gate']
        taxiing_aircraft = [a for a in holding_aircraft if a.state.value == 'taxiing_to_gate']
        unassigned_aircraft = [a for a in holding_aircraft if a.state.value == 'approaching' and a.assigned_runway is None]
        
        # Draw aircraft in organized rows with proper spacing
        start_x = hold_area_x + 20
        start_y = hold_area_y + 40
        circle_radius = 8
        spacing_x = 40  # Increased spacing to prevent text overlap
        spacing_y = 35  # Increased vertical spacing for text labels
        aircraft_per_row = 4  # Reduced to fit properly with text labels
        
        current_x = start_x
        current_y = start_y
        count = 0
        
        # Draw at-gate aircraft (orange)
        for aircraft in gate_aircraft[:12]:  # Max 12 aircraft in hold area (3 rows of 4)
            pos = (current_x, current_y)
            pygame.draw.circle(self.screen, COLORS['aircraft_at_gate'], pos, circle_radius)
            pygame.draw.circle(self.screen, COLORS['text'], pos, circle_radius, 1)
            
            # Draw callsign
            if len(aircraft.callsign) > 5:
                display_name = aircraft.callsign[:5]
            else:
                display_name = aircraft.callsign
            text = self.font_small.render(display_name, True, COLORS['text'])
            text_rect = text.get_rect(center=(current_x, current_y - 15))
            self.screen.blit(text, text_rect)
            
            # Draw gate number if assigned
            if aircraft.assigned_gate is not None:
                gate_text = self.font_small.render(f"G{aircraft.assigned_gate}", True, COLORS['text'])
                gate_rect = gate_text.get_rect(center=(current_x, current_y + 15))
                self.screen.blit(gate_text, gate_rect)
            
            count += 1
            current_x += spacing_x
            if count % aircraft_per_row == 0:
                current_x = start_x
                current_y += spacing_y
        
        # Draw taxiing aircraft (blue)
        for aircraft in taxiing_aircraft[:12-len(gate_aircraft)]:
            if count >= 12:
                break
            pos = (current_x, current_y)
            pygame.draw.circle(self.screen, COLORS['aircraft_taxiing'], pos, circle_radius)
            pygame.draw.circle(self.screen, COLORS['text'], pos, circle_radius, 1)
            
            # Draw callsign
            if len(aircraft.callsign) > 5:
                display_name = aircraft.callsign[:5]
            else:
                display_name = aircraft.callsign
            text = self.font_small.render(display_name, True, COLORS['text'])
            text_rect = text.get_rect(center=(current_x, current_y - 15))
            self.screen.blit(text, text_rect)
            
            count += 1
            current_x += spacing_x
            if count % aircraft_per_row == 0:
                current_x = start_x
                current_y += spacing_y
        
        # Draw unassigned aircraft (green with question mark)
        for aircraft in unassigned_aircraft[:12-len(gate_aircraft)-len(taxiing_aircraft)]:
            if count >= 12:
                break
            pos = (current_x, current_y)
            pygame.draw.circle(self.screen, COLORS['aircraft_approaching'], pos, circle_radius)
            pygame.draw.circle(self.screen, COLORS['text'], pos, circle_radius, 1)
            
            # Draw question mark for unassigned
            question_text = self.font_small.render("?", True, COLORS['text'])
            question_rect = question_text.get_rect(center=pos)
            self.screen.blit(question_text, question_rect)
            
            # Draw callsign
            if len(aircraft.callsign) > 5:
                display_name = aircraft.callsign[:5]
            else:
                display_name = aircraft.callsign
            text = self.font_small.render(display_name, True, COLORS['text'])
            text_rect = text.get_rect(center=(current_x, current_y - 15))
            self.screen.blit(text, text_rect)
            
            count += 1
            current_x += spacing_x
            if count % aircraft_per_row == 0:
                current_x = start_x
                current_y += spacing_y
        
        # Show overflow count if needed
        total_holding = len(holding_aircraft)
        if total_holding > 12:
            overflow_text = self.font_small.render(f"+{total_holding - 12} more", True, COLORS['text'])
            self.screen.blit(overflow_text, (hold_area_x + 5, hold_area_y + hold_area_height - 20))
    
    def draw_aircraft_colors_legend(self):
        """Draw aircraft colors legend beside the hold/stop area."""
        config = get_config()
        # Define legend items
        legend_items = [
            ("Approaching", COLORS['aircraft_approaching']),
            ("Holding", (255, 165, 0)),  # Orange for holding pattern
            ("Landing", COLORS['aircraft_landing']),
            ("Go-Around", COLORS['aircraft_go_around']),
            ("Taxiing", COLORS['aircraft_taxiing']),
            ("At Gate", COLORS['aircraft_at_gate']),
            ("Boarding/Deboarding", COLORS['aircraft_boarding']),
            ("Departing", COLORS['aircraft_departing']),
            ("Crashed", (255, 0, 0)),
            ("High Fuel", (0, 255, 0)),
            ("Low Fuel", (255, 255, 0)),
            ("Critical Fuel", (255, 0, 0))
        ]
        
        # Position legend to the left of hold/stop area
        hold_area_width = 220
        hold_area_height = 140
        hold_area_x = config.airport.airport_width - hold_area_width - 20
        hold_area_y = config.airport.airport_height - hold_area_height - 20
        
        # Legend positioned to the left of hold area
        legend_width = 180
        legend_height = 270  # Height for all legend items (increased for go-around state)
        legend_x = hold_area_x - legend_width - 20
        
        # Position legend so its bottom aligns with the bottom of hold/stop area
        # legend_y + legend_height = hold_area_y + hold_area_height
        legend_y = hold_area_y + hold_area_height - legend_height
        
        # Ensure legend stays on screen
        if legend_y < 10:
            legend_y = 10
        if legend_x < 10:
            legend_x = 10
        
        # Draw legend background
        legend_rect = pygame.Rect(legend_x, legend_y, legend_width, legend_height)
        pygame.draw.rect(self.screen, (40, 40, 40), legend_rect)  # Dark background
        pygame.draw.rect(self.screen, COLORS['text'], legend_rect, 2)  # White border
        
        # Draw title
        legend_title = self.font_medium.render("Aircraft Colors", True, COLORS['text'])
        title_rect = legend_title.get_rect()
        title_x = legend_x + (legend_width - title_rect.width) // 2
        self.screen.blit(legend_title, (title_x, legend_y + 10))
        pygame.draw.line(self.screen, COLORS['text'], 
                        (legend_x + 10, legend_y + 32), (legend_x + legend_width - 10, legend_y + 32), 1)
        
        # Draw legend items
        for i, (label, color) in enumerate(legend_items):
            item_y = legend_y + 40 + i * 18  # Good spacing for legend items
            # Draw color circle
            pygame.draw.circle(self.screen, color, (legend_x + 20, item_y + 8), 6)
            pygame.draw.circle(self.screen, COLORS['text'], (legend_x + 20, item_y + 8), 6, 1)
            # Draw label
            text = self.font_small.render(label, True, COLORS['text'])
            self.screen.blit(text, (legend_x + 35, item_y + 2))
    
    def draw_ui_panel(self):
        """Draw the UI control panel."""
        config = get_config()
        panel_x = config.airport.airport_width
        panel_width = 350
        
        # Draw panel background
        panel_rect = pygame.Rect(panel_x, 0, panel_width, self.screen_height)
        pygame.draw.rect(self.screen, COLORS['ui_panel'], panel_rect)
        pygame.draw.line(self.screen, COLORS['text'], (panel_x, 0), (panel_x, self.screen_height), 2)
        
        # Draw title with better styling
        title = self.font_large.render("Air Traffic Control", True, COLORS['text'])
        self.screen.blit(title, (panel_x + 20, 20))
        
        # Draw underline
        pygame.draw.line(self.screen, COLORS['text'], 
                        (panel_x + 20, 50), (panel_x + 300, 50), 2)
        
        # Draw status section with better spacing 
        status_y = 210  # Position properly below buttons (buttons end at y=195)
        
        # Status section title with separator line
        status_title = self.font_medium.render("System Status", True, COLORS['text'])
        self.screen.blit(status_title, (panel_x + 20, status_y))
        pygame.draw.line(self.screen, COLORS['text'], 
                        (panel_x + 20, status_y + 22), (panel_x + 150, status_y + 22), 1)
        
        # Draw simulation status
        status_text = "RUNNING" if self.simulation.running else "STOPPED"
        status_color = COLORS['aircraft_approaching'] if self.simulation.running else COLORS['gate_occupied']
        status = self.font_small.render(f"Simulation: {status_text}", True, status_color)
        self.screen.blit(status, (panel_x + 20, status_y + 35))
        
        # Draw mode
        if self.simulation.manual_mode:
            mode_text = "MANUAL"
        else:
            # Show actual AI name instead of generic "AUTO AI"
            # AI manager is accessible through self.simulation.atc.ai_manager
            if (hasattr(self.simulation, 'atc') and hasattr(self.simulation.atc, 'ai_manager') 
                and self.simulation.atc.ai_manager.current_ai):
                ai_name = self.simulation.atc.ai_manager.current_ai.name
                # Simplify AI name for display (remove "AI-" prefix and model details)
                if ai_name.startswith("OllamaAI-"):
                    mode_text = f"OLLAMA ({ai_name.split('-', 1)[1]})"
                elif ai_name.startswith("RuleBasedAI"):
                    mode_text = "RULE BASED"
                elif ai_name.startswith("RemoteAI-"):
                    mode_text = "REMOTE AI"
                else:
                    mode_text = ai_name.upper()
            else:
                mode_text = "AUTO AI"
        
        mode_color = COLORS['selected'] if self.simulation.manual_mode else COLORS['text']
        mode = self.font_small.render(f"Control Mode: {mode_text}", True, mode_color)
        self.screen.blit(mode, (panel_x + 20, status_y + 55))
        
        # Draw current AI and model info
        if (hasattr(self.simulation, 'atc') and hasattr(self.simulation.atc, 'ai_manager') 
            and self.simulation.atc.ai_manager.current_ai):
            ai_name = self.simulation.atc.ai_manager.current_ai.name
            # Truncate long AI names for display
            display_name = ai_name if len(ai_name) <= 28 else ai_name[:25] + "..."
            ai_text = self.font_small.render(f"AI Model: {display_name}", True, COLORS['text'])
            self.screen.blit(ai_text, (panel_x + 20, status_y + 75))
        
        # Draw aircraft count
        count = self.font_small.render(f"Aircraft Count: {len(self.airport.aircraft)}", True, COLORS['text'])
        self.screen.blit(count, (panel_x + 20, status_y + 95))
        
        # Draw crash statistics
        state = self.simulation.get_simulation_state()
        crashes = self.font_small.render(f"Total Crashes: {state.get('total_crashes', 0)}", True, COLORS['gate_occupied'])
        self.screen.blit(crashes, (panel_x + 20, status_y + 115))
        
        # Draw fuel warnings
        low_fuel_aircraft = [a for a in self.airport.aircraft if hasattr(a, 'is_low_fuel') and a.is_low_fuel()]
        critical_fuel_aircraft = [a for a in self.airport.aircraft if hasattr(a, 'is_critical_fuel') and a.is_critical_fuel()]
        
        fuel_warning = self.font_small.render(f"Low Fuel: {len(low_fuel_aircraft)} | Critical: {len(critical_fuel_aircraft)}", True, 
                                            COLORS['gate_occupied'] if len(critical_fuel_aircraft) > 0 else COLORS['text'])
        self.screen.blit(fuel_warning, (panel_x + 20, status_y + 135))
        
        # Draw runway queue display
        queue_y = status_y + 160  # Increased padding to avoid overlap with fuel warnings
        queue_title = self.font_medium.render("Runway Queues", True, COLORS['text'])
        self.screen.blit(queue_title, (panel_x + 20, queue_y))
        pygame.draw.line(self.screen, COLORS['text'], 
                        (panel_x + 20, queue_y + 22), (panel_x + 150, queue_y + 22), 1)
        
        # Calculate queue section height for proper spacing
        queue_section_height = 35 + len(self.airport.runways) * 45
        
        for runway_idx, runway in enumerate(self.airport.runways):
            runway_y = queue_y + 35 + runway_idx * 45  # More spacing between runways
            
            # Runway header
            runway_status = "BUSY" if runway.state.value != "available" else "OPEN"
            status_color = COLORS['gate_occupied'] if runway.state.value != "available" else COLORS['aircraft_approaching']
            runway_header = self.font_small.render(f"RW{runway.id}: {runway_status}", True, status_color)
            self.screen.blit(runway_header, (panel_x + 20, runway_y))
            
            # Find aircraft queued for this runway (approaching, landing, or taxiing to runway)
            queued_aircraft = [a for a in self.airport.aircraft 
                             if (a.assigned_runway == runway.id and 
                                 a.state.value in ['approaching', 'landing', 'taxiing_to_runway']) or
                                (a.state.value == 'approaching' and a.assigned_runway is None)]
            
            if queued_aircraft:
                queue_text = ", ".join([a.callsign for a in queued_aircraft[:3]])  # Show max 3
                if len(queued_aircraft) > 3:
                    queue_text += f" +{len(queued_aircraft) - 3}"
                queue_display = self.font_small.render(f"  Queue: {queue_text}", True, COLORS['text'])
                self.screen.blit(queue_display, (panel_x + 25, runway_y + 18))
            else:
                no_queue = self.font_small.render("  Queue: Empty", True, COLORS['text'])
                self.screen.blit(no_queue, (panel_x + 25, runway_y + 18))
        
        # Draw selected aircraft info (positioned after runway queues)
        selected_y = queue_y + queue_section_height + 15  # Position after runway queues
        selected_section_height = 0  # Default height when no aircraft selected
        
        if self.selected_aircraft:
            aircraft = self.airport.get_aircraft(self.selected_aircraft)
            if aircraft:
                selected_text = self.font_medium.render("Selected Aircraft:", True, COLORS['selected'])
                self.screen.blit(selected_text, (panel_x + 20, selected_y))
                pygame.draw.line(self.screen, COLORS['selected'], 
                                (panel_x + 20, selected_y + 22), (panel_x + 170, selected_y + 22), 1)
                
                # Build state display with crash reason if crashed
                state_display = aircraft.state.value
                if aircraft.state.value == "crashed" and hasattr(aircraft, 'crash_reason') and aircraft.crash_reason:
                    state_display = f"{aircraft.state.value} ({aircraft.crash_reason})"
                
                info_lines = [
                    f"Callsign: {aircraft.callsign}",
                    f"State: {state_display}",
                    f"Type: {aircraft.aircraft_type.value}",  # Use .value for human-readable name
                    f"Runway: {aircraft.assigned_runway}",
                    f"Gate: {aircraft.assigned_gate}",
                    f"Fuel: {aircraft.fuel:.1f}%"
                ]
                
                # Add fuel status if applicable
                if hasattr(aircraft, 'is_critical_fuel') and aircraft.is_critical_fuel():
                    info_lines.append("⚠️ CRITICAL FUEL!")
                elif hasattr(aircraft, 'is_low_fuel') and aircraft.is_low_fuel():
                    info_lines.append("⚠️ Low Fuel")
                
                for i, line in enumerate(info_lines):
                    text = self.font_small.render(line, True, COLORS['text'])
                    self.screen.blit(text, (panel_x + 20, selected_y + 35 + i * 18))
                
                selected_section_height = 35 + len(info_lines) * 18 + 20  # Title + lines + padding
        
        # Draw controls help section (positioned after selected aircraft or runway queues)
        help_y = selected_y + selected_section_height + 15  # Position after selected aircraft with padding
        
        if self.simulation.manual_mode:
            help_title = self.font_medium.render("Manual Controls", True, COLORS['selected'])
            self.screen.blit(help_title, (panel_x + 20, help_y))
            pygame.draw.line(self.screen, COLORS['selected'], 
                            (panel_x + 20, help_y + 22), (panel_x + 150, help_y + 22), 1)
            
            controls = [
                "• Click aircraft to select",
                "• L - Assign landing", 
                "• G - Assign gate",
                "• T - Assign takeoff",
                "• H - Hold pattern"
            ]
            
            for i, control in enumerate(controls):
                text = self.font_small.render(control, True, COLORS['text'])
                self.screen.blit(text, (panel_x + 20, help_y + 30 + i * 18))
        
        # AI Models section removed - using top buttons instead
        
        # Draw buttons
        for button in self.buttons:
            button.draw(self.screen)
    
    def render(self):
        """Main render function."""
        # Clear screen
        self.screen.fill(COLORS['background'])
        
        # Draw airport elements
        for runway in self.airport.runways:
            self.draw_runway(runway)
        
        for gate in self.airport.gates:
            self.draw_gate(gate)
        
        for aircraft in self.airport.aircraft:
            self.draw_aircraft(aircraft)
        
        # Draw hold/stop area
        self.draw_hold_stop_area()
        
        # Draw aircraft colors legend beside hold/stop area
        self.draw_aircraft_colors_legend()
        
        # Draw UI
        self.draw_ui_panel()
        
        # Update display
        pygame.display.flip()
    
    def run(self):
        """Main graphics loop."""
        while self.running:
            # Handle events
            if not self.handle_events():
                break
            
            # Update simulation
            dt = self.clock.tick(60) / 1000.0  # 60 FPS, dt in seconds
            self.simulation.update(dt)
            
            # Render
            self.render()
        
        pygame.quit()
        return True 