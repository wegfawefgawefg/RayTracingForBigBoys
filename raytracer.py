import math
import random
from tqdm import tqdm
from PIL import Image

class Vec3:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def __add__(self, other):
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other):
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, other):
        return Vec3(self.x * other, self.y * other, self.z * other)

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        return Vec3(self.x / other, self.y / other, self.z / other)

    def mag(self):
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)

    def norm(self):
        length = self.mag()
        return Vec3(
            x=self.x / length,
            y=self.y / length,
            z=self.z / length,
        )

    def dot(self, other):
        return self.x*other.x + self.y*other.y + self.z*other.z

    def clamp(self, low, high):
        return Vec3(
            x=min(max(self.x, low), high),
            y=min(max(self.y, low), high),
            z=min(max(self.z, low), high),
        )

    def __repr__(self):
        return (self.x, self.y, self.z).__repr__()

    @classmethod
    def white(self):
        return Vec3(1.0, 1.0, 1.0)

    @classmethod
    def black(self):
        return Vec3(0.0, 0.0, 0.0)

    @classmethod
    def random(self):
        return Vec3(random.random(), random.random(), random.random())

class Ray:
    def __init__(self, origin, dir):
        self.origin = origin
        self.dir = dir.norm()

class Material:
    def __init__(self, color, 
            ambient=0.05, 
            diffuse=0.25, 
            specular=0.1,
            reflective=1.0):
        self.color = color
        self.ambient = ambient
        self.diffuse = diffuse
        self.specular = specular
        self.reflective = reflective    

class Light:
    def __init__(self, pos, color=Vec3.white()):
        self.pos = pos
        self.color = color

class Sphere:
    def __init__(self, center, radius, material):
        self.center = center
        self.radius = radius
        self.material = material

    def intersects(self, ray):
        to_sphere = self.center - ray.origin
        t = to_sphere.dot(ray.dir)
        if t < 0:
            return None
        perp_point = ray.origin + ray.dir * t
        shortest_line = perp_point - self.center
        y = shortest_line.mag()
        if y <= self.radius:    #   hit
            x = math.sqrt(self.radius**2 - y**2)
            dist = t - x
            return dist
        else:   #   miss
            return None

    def get_normal(self, hit_pos):
        return (hit_pos - self.center).norm()

class Scene:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.cam = Vec3(
            x=width / 2,
            y=height / 2,
            z=-width / 2
        )
        self.NUM_SPHERES = 30
        self.NUM_LIGHTS = 20
        self.lights = []
        self.shapes = []

        for _ in range(self.NUM_SPHERES):
            sphere = Sphere(
                center=Vec3(
                    x=random.random() * width,
                    y=random.random() * height,
                    z=width / 2 + random.random() * width),
                radius=random.random() * width / 7,
                material=Material(color=Vec3.random())
            )
            self.shapes.append(sphere)

        for _ in range(self.NUM_LIGHTS):
            light = Light(
                pos=Vec3(
                    x=width / 2 + (random.random() - 0.5) * 2 * width * 2,
                    y=height / 2 + (random.random() - 0.5) * 2 * height * 2,
                    z=width / 2 + random.random() * width),
                color=Vec3.random()
            )
            self.lights.append(light)

def render_scene(scene, max_bounces=3):
    #   make pixel buffer
    pixels = []
    for y in range(scene.height):
        row = []
        for x in range(scene.width):
            pixel = Vec3.black()
            row.append(pixel)
        pixels.append(row)

    #   do actual raytracing
    for y in tqdm(range(scene.height)):
        for x in range(scene.width):
            target = Vec3(x, y, 0)
            ray = Ray(
                origin=scene.cam,
                dir=target - scene.cam)
            pixels[y][x] = raytrace(ray, scene, max_bounces)
    return pixels

def raytrace(ray, scene, max_bounces, depth=0):
    if depth == max_bounces:
        return Vec3.black()

    #   find closest ray shape intersection
    shape_hit = None
    min_dist = math.inf
    for shape in scene.shapes:
        dist = shape.intersects(ray)
        if dist is not None:
            if shape_hit is None:
                shape_hit = shape
                min_dist = dist
            elif dist < min_dist:
                shape_hit = shape
                min_dist = dist
    if shape_hit is None:
        return Vec3.black()
    dist = min_dist

    hit_pos = ray.origin + ray.dir * dist
    hit_normal = shape_hit.get_normal(hit_pos)
    color = color_at(scene, ray, shape_hit, hit_pos, hit_normal)

    bounce_ray = Ray(
        origin=hit_pos + hit_normal * 0.001,
        dir=ray.dir - (2 * ray.dir.dot(hit_normal) * hit_normal)
    )
    color += raytrace(bounce_ray, scene, max_bounces, depth + 1)
    return color    

def color_at(scene, ray, shape_hit, hit_pos, hit_normal):
    color = shape_hit.material.color * shape_hit.material.ambient

    for light in scene.lights:
        to_light = (light.pos - hit_pos).norm()
        to_cam = (scene.cam - hit_pos).norm()

        #   diffuse lighting model
        color += (
            shape_hit.material.color
            * shape_hit.material.diffuse
            * max(hit_normal.dot(to_light), 0.0)
        )

        #   specular lighting model
        halfway = (to_light + to_cam).norm()
        color += (
            light.color
            * shape_hit.material.specular
            * max(halfway.dot(hit_normal), 0.0) ** 30
        )

    return color

def write_as_png(file_name, pixels, show_when_done=False):
    height = len(pixels)
    width = len(pixels[0])

    file_image = Image.new('RGB', (width, height), color='black')
    image_pixels = file_image.load()
    for y in range(height):
        for x in range(width):
            pixel = pixels[y][x]
            pixel = pixel.clamp(0.0, 1.0) * 255.0
            image_pixels[x, height - 1 - y] = (
                int(pixel.x),
                int(pixel.y),
                int(pixel.z)
            )
    
    file_image.save(file_name + ".png")
    if show_when_done:
        file_image.show()

def main():
    resolutions = [(20, 20), (200, 200), (500, 500),
        (1920, 1080), (4096, 2160), (7680, 4320)]
    width, height = resolutions[3]

    scene = Scene(width, height)
    pixels = render_scene(scene, max_bounces=5)
    write_as_png("render", pixels, show_when_done=True)

if __name__ == "__main__":
    main()    