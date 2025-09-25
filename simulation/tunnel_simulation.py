import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.path import Path
from tqdm import tqdm
import os
import subprocess

# 1. PARÁMETROS DE LA SIMULACIÓN Y VISUALIZACIÓN

WIDTH, HEIGHT = 1920, 1080
DPI = 120
NUM_FRAMES = 1200
FPS = 30
NUM_PARTICLES = 5000       # Aumentado para un fluido denso y continuo
PARTICLE_SIZE_MIN, PARTICLE_SIZE_MAX = 1, 6
BASE_VELOCITY = 50.0
BOOST_FACTOR = 1.0
TURBULENCE_STRENGTH = 10.0
DT = 1.0 / FPS

# 2. DEFINICIÓN DE LA GEOMETRÍA DEL TÚNEL
puntos_originales = [
    (0, 19.5), (31, 19.5), (89, 7.5), (134, 7.5), (234, 14),
    (234, -14), (134, -7.5), (89, -7.5), (31, -19.5), (0, -19.5)
]


def procesar_geometria(puntos, target_width, target_height, padding=100):
    puntos_np = np.array(puntos, dtype=float)
    min_c, max_c = puntos_np.min(axis=0), puntos_np.max(axis=0)
    puntos_np -= min_c
    dims = max_c - min_c
    scale = min((target_width - 2 * padding) /
                dims[0], (target_height - 2 * padding) / dims[1])
    puntos_np *= scale
    new_dims = puntos_np.max(axis=0)
    offset = (np.array([target_width, target_height]) - new_dims) / 2
    return puntos_np + offset


vertices_escalados = procesar_geometria(puntos_originales, WIDTH, HEIGHT)
tunel_path = Path(vertices_escalados)
inlet_start, inlet_end = vertices_escalados[9], vertices_escalados[0]
gorge_x_start, gorge_x_end = vertices_escalados[2][0], vertices_escalados[3][0]
outlet_x = vertices_escalados[5][0]

# 3. LÓGICA DEL SOLVER DE FLUIDO (CON PRE-POBLACIÓN)


class ParticleFluidSimulator:
    def __init__(self):
        # Pre-poblamos el túnel con partículas distribuidas aleatoriamente
        print("Pre-poblando el túnel con partículas...")
        self.positions = self.generate_points_in_polygon(
            NUM_PARTICLES, tunel_path)

        # Las partículas empiezan con velocidad cero (aire estático)
        self.velocities = np.zeros((NUM_PARTICLES, 2))
        # Edades iniciales aleatorias
        self.ages = np.random.rand(NUM_PARTICLES) * 5
        self.sizes = np.zeros(NUM_PARTICLES)

    def generate_points_in_polygon(self, n_points, path):
        """Genera N puntos aleatorios que se encuentran dentro del polígono del túnel."""
        min_x, min_y, max_x, max_y = path.vertices.min(axis=0)[0], path.vertices.min(axis=0)[1], \
            path.vertices.max(axis=0)[0], path.vertices.max(axis=0)[1]

        points = []
        while len(points) < n_points:
            # Generar un lote de puntos en la caja delimitadora
            random_points = np.random.rand(n_points, 2)
            random_points[:, 0] = random_points[:, 0] * (max_x - min_x) + min_x
            random_points[:, 1] = random_points[:, 1] * (max_y - min_y) + min_y

            # Mantener solo los puntos que están realmente dentro del polígono
            inside_mask = path.contains_points(random_points)
            points.extend(random_points[inside_mask])

        return np.array(points[:n_points])

    def get_velocity_field(self, pos):
        vel_field = np.zeros_like(pos)
        vel_field[:, 0] = BASE_VELOCITY
        y_center = HEIGHT / 2
        dist = np.abs(pos[:, 1] - y_center)
        h_half = (inlet_end[1] - inlet_start[1]) / 2
        boundary_factor = np.clip(1 - (dist / (h_half * 1.5))**2, 0.1, 1.0)
        vel_field[:, 0] *= boundary_factor
        in_gorge = (pos[:, 0] > gorge_x_start) & (pos[:, 0] < gorge_x_end)
        vel_field[in_gorge, 0] *= BOOST_FACTOR
        turbulence = (np.random.rand(len(pos), 2) - 0.5) * \
            2 * TURBULENCE_STRENGTH
        vel_field += turbulence
        return vel_field

    def reset_particles(self, indices):
        num_to_reset = len(indices)
        if num_to_reset == 0:
            return
        ratios = np.random.rand(num_to_reset)
        new_x = inlet_start[0] + \
            np.random.rand(num_to_reset) * 5  # Pequeño jitter
        new_y = inlet_start[1] * (1 - ratios) + inlet_end[1] * ratios
        self.positions[indices] = np.column_stack((new_x, new_y))
        self.ages[indices] = np.random.rand(num_to_reset) * 0.1

    def update(self):
        self.velocities = self.get_velocity_field(self.positions)
        self.positions += self.velocities * DT
        self.ages += DT

        outside_mask = ~tunel_path.contains_points(self.positions)
        escaped_mask = self.positions[:, 0] > outlet_x
        reset_mask = outside_mask | escaped_mask
        indices_to_reset = np.where(reset_mask)[0]
        self.reset_particles(indices_to_reset)

        speeds = np.linalg.norm(self.velocities, axis=1)
        norm_speeds = np.clip(
            speeds / (BASE_VELOCITY * BOOST_FACTOR * 1.5), 0, 1)
        self.sizes = PARTICLE_SIZE_MAX - \
            (PARTICLE_SIZE_MAX - PARTICLE_SIZE_MIN) * norm_speeds


# 4. BUCLE PRINCIPAL Y RENDERIZADO
output_dir = "tunnel_simulation"
os.makedirs(output_dir, exist_ok=True)
simulator = ParticleFluidSimulator()

for i in tqdm(range(NUM_FRAMES), desc="Simulando y Renderizando"):
    simulator.update()

    fig, ax = plt.subplots(figsize=(WIDTH/DPI, HEIGHT/DPI), dpi=DPI)
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    fig.patch.set_facecolor('black')
    ax.set_facecolor('black')
    ax.set_xlim(0, WIDTH)
    ax.set_ylim(0, HEIGHT)
    ax.axis('off')

    path_patch = patches.PathPatch(
        tunel_path, facecolor='none', edgecolor='#444444', lw=2)
    ax.add_patch(path_patch)

    ax.scatter(simulator.positions[:, 0], simulator.positions[:, 1],
               s=simulator.sizes, c='cyan', alpha=0.6, marker='.')

    plt.savefig(f"{output_dir}/frame_{i:04d}.png")
    plt.close()

print(f"\nSimulación finalizada... {
      NUM_FRAMES} fotogramas guardados en '{output_dir}'.")

# 5. CREACIÓN DEL VIDEO FINAL CON FFMPEG

try:
    print("Creando video final con FFmpeg...")
    subprocess.run([
        'ffmpeg', '-framerate', str(FPS), '-i', f'{output_dir}/frame_%04d.png',
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-y', 'tunnel_simulation.mp4'
    ], check=True)
    print("\n¡Video 'tunnel_simulation.mp4' creado con éxito!")
except FileNotFoundError:
    print(f"\nError: FFmpeg no está instalado. Por favor, ejecútalo manualmente:\n"
          f"ffmpeg -framerate {FPS} -i {output_dir}/frame_%04d.png -c:v 'libx264' -pix_fmt yuv420p 'tunnel_simulation.mp4'")
except subprocess.CalledProcessError as e:
    print(f"\nError durante la creación del video con FFmpeg: {e}")
