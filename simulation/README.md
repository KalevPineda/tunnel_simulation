


# Simulación de Túnel de Viento Basada en Partículas

![Demo animada](tunnel_simulation.gif)

## Resumen

Script de Python autocontenido que genera una simulación visual de un flujo de fluido (viento) dentro de una geometría de túnel de viento en 2D. La simulación utiliza un **método Lagrangiano basado en partículas**, donde el comportamiento colectivo de miles de partículas individuales emula las propiedades macroscópicas de un fluido.

El programa renderiza una secuencia de imágenes en alta definición (1920x1080) que luego son ensambladas automáticamente en un archivo de video MP4 utilizando FFmpeg. El enfoque principal es lograr un comportamiento visualmente plausible que respete principios fundamentales de la dinámica de fluidos, como el **Principio de Continuidad** y la **capa límite**.

## Funcionamiento e Implementación Técnica

El script está estructurado en cinco secciones lógicas principales.

### 1. Definición de Parámetros Globales

Esta sección inicial configura todas las variables que controlan la simulación y la salida. Se dividen en:
-   **Parámetros de Visualización:** `WIDTH`, `HEIGHT`, `DPI`, `NUM_FRAMES`, `FPS`. Definen la resolución, duración y fluidez del video final.
-   **Parámetros de Simulación:** Controlan la "física" del fluido.
    -   `NUM_PARTICLES`: El número de agentes discretos que representan el fluido. Afecta directamente a la densidad visual y al coste computacional.
    -   `BASE_VELOCITY`: La velocidad de flujo laminar base en la sección de admisión, medida en píxeles por segundo.
    -   `BOOST_FACTOR`: Un multiplicador que incrementa la velocidad en la sección estrecha (garganta), simulando el **Principio de Continuidad** (conservación de la masa).
    -   `TURBULENCE_STRENGTH`: La magnitud de un vector de perturbación aleatorio aplicado a cada partícula en cada paso de tiempo, simulando el comportamiento caótico de un flujo turbulento.

### 2. Procesamiento de la Geometría

El túnel de viento se define por un conjunto de vértices 2D (`puntos_originales`).
1.  **Normalización y Escalado:** La función `procesar_geometria` toma estos puntos y los transforma para que se ajusten al lienzo de salida (1920x1080). Realiza una traslación para que el punto mínimo sea (0,0), calcula un factor de escala para que la figura ocupe la mayor parte del lienzo (con un `padding`) y finalmente realiza otra traslación para centrar perfectamente la figura.
2.  **Creación de la Ruta (`Path`):** Los vértices procesados se utilizan para crear un objeto `matplotlib.path.Path`. Este objeto es computacionalmente muy eficiente y se convierte en la herramienta principal para las pruebas de colisión, permitiendo verificar si un punto (o un array de puntos) se encuentra dentro de la geometría del túnel.

### 3. El Solver de Fluido (`ParticleFluidSimulator`)

Esta clase encapsula toda la lógica del comportamiento del fluido.

-   **Inicialización (`__init__`)**:
    -   El paso más crucial es la **pre-población del túnel**. En lugar de inyectar partículas, se llama a la función `generate_points_in_polygon`. Esta utiliza una técnica de "muestreo por rechazo": genera puntos aleatorios dentro de la caja delimitadora del túnel y se queda únicamente con aquellos que `tunel_path.contains_points()` confirma que están dentro de la geometría. Esto asegura que la simulación comience con un fluido estático y distribuido uniformemente.
    -   Se inicializan los arrays de NumPy para las posiciones, velocidades y edades de todas las partículas.

-   **Campo de Velocidad (`get_velocity_field`)**:
    -   Esta función es el corazón del solver. No calcula interacciones partícula-partícula, sino que define un **campo de velocidad Euleriano** invisible que guía a las partículas Lagrangianas.
    -   Para cualquier array de posiciones `pos`, calcula el vector de velocidad del "viento" en esos puntos.
    -   Implementa la **capa límite** mediante una función parabólica: la velocidad es máxima en el centro vertical del túnel (`y_center`) y disminuye a medida que las partículas se acercan a las paredes superior e inferior.
    -   Aplica el `BOOST_FACTOR` a las partículas que se encuentran en la región de la garganta.
    -   Finalmente, suma un vector de **turbulencia** (ruido aleatorio) para romper el flujo laminar y crear un comportamiento más realista.

-   **Actualización (`update`)**:
    -   Este método se llama una vez por cada fotograma.
    -   **Asigna la velocidad del campo:** La velocidad de cada partícula se establece directamente a la velocidad del campo en su posición actual (`self.velocities = self.get_velocity_field(self.positions)`).
    -   **Integración de Euler:** Las posiciones se actualizan con la nueva velocidad y el paso de tiempo `DT` (`self.positions += self.velocities * DT`).
    -   **Lógica de Reciclaje:** Se identifican las partículas que han salido de los límites (`outside_mask` y `escaped_mask`) y se las reubica en la entrada del túnel llamando a `reset_particles`. Esto mantiene la densidad de partículas constante.

### 4. Bucle Principal y Renderizado

Un bucle `for` itera `NUM_FRAMES` veces. En cada iteración:
1.  Se llama a `simulator.update()` para avanzar la física de la simulación.
2.  Se crea una figura de Matplotlib con las dimensiones y DPI exactos para producir una imagen de 1920x1080. Se eliminan todos los márgenes y ejes (`subplots_adjust` y `axis('off')`).
3.  Se dibuja el contorno del túnel (`PathPatch`).
4.  Se dibujan todas las partículas en sus nuevas posiciones usando `ax.scatter()`.
5.  La figura completa se guarda como un archivo PNG en una carpeta de salida (`tunnel_simulation`).
6.  `plt.close()` se llama para liberar la memoria, lo cual es crucial para evitar que el programa se colapse al generar cientos de imágenes.

### 5. Ensamblaje del Video

Una vez que todas las imágenes han sido generadas, el script utiliza el módulo `subprocess` de Python para llamar a **FFmpeg**, una potente herramienta externa de línea de comandos.
-   El comando le indica a FFmpeg que tome la secuencia de imágenes (`frame_%04d.png`), las interprete a una velocidad de `FPS` fotogramas por segundo, y las codifique usando el códec de video `libx264` (el estándar para H.264/MP4) para crear el archivo final `tunnel_simulation.mp4`.

## Instrucciones de Instalación y Uso

### Prerrequisitos

Necesitas tener Python 3 instalado, así como las siguientes librerías de Python y una herramienta externa.

1.  **Librerías de Python:** Puedes instalarlas todas con un solo comando usando `pip`:
    ```bash
    pip install numpy matplotlib tqdm
    ```
2.  **FFmpeg:** Esta es una dependencia externa esencial para crear el video.
    -   **macOS (usando Homebrew):**
        ```bash
        brew install ffmpeg
        ```
    -   **Linux (Debian/Ubuntu):**
        ```bash
        sudo apt-get update
        sudo apt-get install ffmpeg
        ```
    -   **Windows:** Descarga el ejecutable desde el [sitio web oficial de FFmpeg](https://ffmpeg.org/download.html) y asegúrate de añadir la carpeta `bin` a la variable de entorno PATH del sistema.

### Ejecución

1.  **Guarda el Código:** Guarda el código proporcionado en un archivo llamado `tunnel_simulation.py`.
2.  **Abre una Terminal:** Navega hasta el directorio donde guardaste el archivo.
    ```bash
    cd /ruta/a/tu/proyecto
    ```
3.  **Ejecuta el Script:**
    ```bash
    python tunnel_simulation.py
    ```

El script comenzará a ejecutarse, mostrando una barra de progreso. Creará una carpeta llamada `tunnel_simulation` y la llenará con los fotogramas generados. Una vez que termine, ensamblará automáticamente el video `tunnel_simulation.mp4` en el mismo directorio.

### Personalización

Para ajustar la simulación, simplemente modifica los valores en la **Sección 1 (PARÁMETROS)** del script. Por ejemplo, para un video más corto y un fluido más denso, podrías cambiar:
```python
NUM_FRAMES = 300       # Para un video de 10 segundos
NUM_PARTICLES = 50000  # Para un fluido mucho más denso
```





