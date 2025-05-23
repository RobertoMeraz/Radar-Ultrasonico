import RPi.GPIO as GPIO
import time
import pygame
import math
import sys

# Configuración de Pygame
pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Radar Ultrasónico")
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLACK = (0, 0, 0)
BLUE = (0, 0, 255)
FONT = pygame.font.SysFont('Arial', 16)

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

# Variables para almacenar los datos del radar
radar_data = []
max_distance = 200  # Distancia máxima a mostrar en cm

def set_servo_angle(angle):
    duty = angle / 18 + 2
    GPIO.output(SERVO_PIN, True)
    pwm.ChangeDutyCycle(duty)
    time.sleep(0.2)  # Tiempo reducido para mejor rendimiento
    GPIO.output(SERVO_PIN, False)
    pwm.ChangeDutyCycle(0)

def get_distance():
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    pulse_start = time.time()
    pulse_end = time.time()
    timeout = time.time() + 0.02  # Timeout reducido a 20ms

    while GPIO.input(ECHO) == 0 and pulse_start < timeout:
        pulse_start = time.time()

    while GPIO.input(ECHO) == 1 and pulse_end < timeout:
        pulse_end = time.time()

    pulse_duration = pulse_end - pulse_start
    distance = pulse_duration * 17150
    distance = max(0, min(round(distance, 2), max_distance))  # Limitar a max_distance
    
    # Filtro simple para eliminar valores erróneos
    if len(radar_data) > 1 and distance > radar_data[-1][1] * 1.5:
        distance = radar_data[-1][1]  # Usar el valor anterior si hay un salto grande
    
    return distance

def draw_radar():
    center_x, center_y = WIDTH // 2, HEIGHT - 50
    radius = min(center_x, center_y) - 20
    
    # Dibujar círculos concéntricos
    for r in range(radius, 0, -radius//5):
        pygame.draw.circle(screen, GREEN, (center_x, center_y), r, 1)
        distance_label = FONT.render(f"{int((r/radius)*max_distance)}cm", True, WHITE)
        screen.blit(distance_label, (center_x + r - 20, center_y))
    
    # Dibujar líneas de ángulo
    for angle in range(0, 181, 30):
        rad_angle = math.radians(angle)
        end_x = center_x + radius * math.sin(rad_angle)
        end_y = center_y - radius * math.cos(rad_angle)
        pygame.draw.line(screen, GREEN, (center_x, center_y), (end_x, end_y), 1)
        angle_label = FONT.render(f"{angle}°", True, WHITE)
        screen.blit(angle_label, (end_x, end_y))
    
    # Dibujar los datos del radar
    if radar_data:
        for i in range(1, len(radar_data)):
            angle_prev, dist_prev = radar_data[i-1]
            angle_curr, dist_curr = radar_data[i]
            
            if dist_prev > 0 and dist_curr > 0:
                prev_rad = math.radians(angle_prev)
                curr_rad = math.radians(angle_curr)
                
                x1 = center_x + (dist_prev/max_distance)*radius * math.sin(prev_rad)
                y1 = center_y - (dist_prev/max_distance)*radius * math.cos(prev_rad)
                
                x2 = center_x + (dist_curr/max_distance)*radius * math.sin(curr_rad)
                y2 = center_y - (dist_curr/max_distance)*radius * math.cos(curr_rad)
                
                pygame.draw.line(screen, RED, (x1, y1), (x2, y2), 2)
                pygame.draw.circle(screen, BLUE, (int(x2), int(y2)), 3)
    
    # Dibujar información de la última medición
    if radar_data:
        last_angle, last_dist = radar_data[-1]
        info_text = f"Ángulo: {last_angle}° - Distancia: {last_dist} cm"
        text_surface = FONT.render(info_text, True, WHITE)
        screen.blit(text_surface, (10, 10))

try:
    print("Radar activo. Presiona Ctrl+C o cierra la ventana para detener.")
    
    clock = pygame.time.Clock()
    running = True
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        
        # Escaneo de izquierda a derecha
        for angle in range(0, 181, 5):  # Paso más fino de 5°
            if not running:
                break
                
            set_servo_angle(angle)
            dist = get_distance()
            radar_data.append((angle, dist))
            
            # Limitar el número de puntos almacenados
            if len(radar_data) > 100:
                radar_data.pop(0)
            
            # Dibujar
            screen.fill(BLACK)
            draw_radar()
            pygame.display.flip()
            clock.tick(30)  # 30 FPS
        
        if not running:
            break
            
        # Escaneo de derecha a izquierda
        for angle in range(180, -1, -5):  # Paso más fino de 5°
            if not running:
                break
                
            set_servo_angle(angle)
            dist = get_distance()
            radar_data.append((angle, dist))
            
            if len(radar_data) > 100:
                radar_data.pop(0)
            
            # Dibujar
            screen.fill(BLACK)
            draw_radar()
            pygame.display.flip()
            clock.tick(30)
    
except KeyboardInterrupt:
    pass

finally:
    pwm.stop()
    GPIO.cleanup()
    pygame.quit()
    print("\nRadar detenido.")
    sys.exit()