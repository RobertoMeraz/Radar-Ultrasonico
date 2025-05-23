import RPi.GPIO as GPIO
import time
import pygame
import math
import sys

# Configuración de colores
class colors:
    black = (0, 0, 0)
    green = (0, 255, 0)
    white = (255, 255, 255)
    red = (255, 0, 0)
    dark_green = (0, 100, 0)
    target_colors = [
        (255, 0, 0),    # Rojo intenso
        (255, 50, 50),   # Rojo claro 1
        (255, 100, 100), # Rojo claro 2
        (255, 150, 150), # Rojo claro 3
        (255, 200, 200)  # Rojo claro 4
    ]

# Configuración de Pygame
pygame.init()
WIDTH, HEIGHT = 1000, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Radar de Media Luna (0°-180°)")
FONT = pygame.font.SysFont('Arial', 20)
LARGE_FONT = pygame.font.SysFont('Arial', 24, bold=True)

# Configuración del servo
SERVO_PIN = 18  # GPIO18 (pin 12)
GPIO.setmode(GPIO.BCM)
GPIO.setup(SERVO_PIN, GPIO.OUT)
pwm = GPIO.PWM(SERVO_PIN, 50)  # PWM a 50Hz
pwm.start(0)

# Configuración del HC-SR04
TRIG = 23  # GPIO23 (pin 16)
ECHO = 24  # GPIO24 (pin 18)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

# Parámetros del radar
max_distance = 200  # 200 cm máximo
radar_center = (WIDTH//2, HEIGHT-50)
radar_radius = min(WIDTH, HEIGHT) - 100
targets = []

class Target:
    def __init__(self, angle, distance):
        self.angle = angle
        self.distance = distance
        self.time = time.time()
        self.color_index = 0

def set_servo_angle(angle):
    duty = angle / 18 + 2
    GPIO.output(SERVO_PIN, True)
    pwm.ChangeDutyCycle(duty)
    time.sleep(0.05)  # Tiempo reducido para mejor rendimiento
    GPIO.output(SERVO_PIN, False)
    pwm.ChangeDutyCycle(0)

def get_distance():
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    pulse_start = time.time()
    pulse_end = time.time()
    timeout = time.time() + 0.02  # Timeout de 20ms

    while GPIO.input(ECHO) == 0 and pulse_start < timeout:
        pulse_start = time.time()

    while GPIO.input(ECHO) == 1 and pulse_end < timeout:
        pulse_end = time.time()

    pulse_duration = pulse_end - pulse_start
    distance = pulse_duration * 17150
    return max(0, min(round(distance, 2), max_distance))

def draw_radar(angle, distance):
    # Fondo negro
    screen.fill(colors.black)
    
    # Dibujar media luna (semicírculo)
    pygame.draw.arc(screen, colors.dark_green, 
                   (radar_center[0]-radar_radius, radar_center[1]-radar_radius, 
                    radar_radius*2, radar_radius*2),
                   math.radians(0), math.radians(180), 2)
    
    # Dibujar círculos concéntricos (solo la mitad superior)
    for r in range(radar_radius, 0, -radar_radius//5):
        pygame.draw.arc(screen, colors.green, 
                       (radar_center[0]-r, radar_center[1]-r, r*2, r*2),
                       math.radians(0), math.radians(180), 1)
        
        # Etiquetas de distancia
        if r != radar_radius:
            dist_text = LARGE_FONT.render(f"{int((r/radar_radius)*max_distance)}", True, colors.green)
            screen.blit(dist_text, (radar_center[0] - r - 10, radar_center[1] - 20))
            screen.blit(dist_text, (radar_center[0] + r - 10, radar_center[1] - 20))
    
    # Dibujar líneas de ángulo
    for deg in range(0, 181, 30):
        rad = math.radians(deg)
        end_x = radar_center[0] + radar_radius * math.cos(rad)
        end_y = radar_center[1] - radar_radius * math.sin(rad)
        pygame.draw.line(screen, colors.green, radar_center, (end_x, end_y), 1)
        
        # Etiquetas de ángulo
        if deg == 0:
            text_pos = (radar_center[0] + radar_radius + 10, radar_center[1] - 10)
        elif deg == 180:
            text_pos = (radar_center[0] - radar_radius - 30, radar_center[1] - 10)
        else:
            text_pos = (end_x - 15, end_y - 10)
        
        angle_text = FONT.render(f"{deg}°", True, colors.green)
        screen.blit(angle_text, text_pos)
    
    # Dibujar línea de barrido
    rad_angle = math.radians(angle)
    end_x = radar_center[0] + radar_radius * math.cos(rad_angle)
    end_y = radar_center[1] - radar_radius * math.sin(rad_angle)
    pygame.draw.line(screen, colors.green, radar_center, (end_x, end_y), 2)
    
    # Panel de información
    pygame.draw.rect(screen, colors.green, (10, 10, 250, 80), 1)
    angle_text = LARGE_FONT.render(f"Ángulo: {angle}°", True, colors.white)
    dist_text = LARGE_FONT.render(f"Distancia: {distance if distance < max_distance else '---'} cm", 
                                True, colors.white)
    screen.blit(angle_text, (20, 20))
    screen.blit(dist_text, (20, 50))
    
    # Dibujar objetivos
    for target in targets[:]:
        # Calcular posición del objetivo
        target_rad = math.radians(target.angle)
        target_dist = (target.distance/max_distance) * radar_radius
        target_x = radar_center[0] + target_dist * math.cos(target_rad)
        target_y = radar_center[1] - target_dist * math.sin(target_rad)
        
        # Dibujar objetivo
        pygame.draw.circle(screen, colors.target_colors[target.color_index], 
                         (int(target_x), int(target_y)), 5)
        
        # Actualizar desvanecimiento
        target.color_index = min(target.color_index + 1, len(colors.target_colors)-1)
        
        # Eliminar objetivos muy antiguos
        if time.time() - target.time > 2.0:
            targets.remove(target)
    
    pygame.display.flip()

try:
    clock = pygame.time.Clock()
    running = True
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        
        # Escaneo de izquierda a derecha (0° a 180°)
        for angle in range(0, 181, 2):
            if not running:
                break
                
            set_servo_angle(angle)
            distance = get_distance()
            
            if distance < max_distance:
                targets.append(Target(angle, distance))
            
            draw_radar(angle, distance)
            clock.tick(30)  # 30 FPS
        
        if not running:
            break
            
        # Escaneo de derecha a izquierda (180° a 0°)
        for angle in range(180, -1, -2):
            if not running:
                break
                
            set_servo_angle(angle)
            distance = get_distance()
            
            if distance < max_distance:
                targets.append(Target(angle, distance))
            
            draw_radar(angle, distance)
            clock.tick(30)

except KeyboardInterrupt:
    pass

finally:
    pwm.stop()
    GPIO.cleanup()
    pygame.quit()
    sys.exit()