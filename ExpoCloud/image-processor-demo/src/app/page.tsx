/**
 * Esta es la página principal de la aplicación.
 * Sirve como el contenedor principal y centra el componente ImageUploader
 * en la pantalla, proporcionando un título y un subtítulo para la demo.
 */

import ImageUploader from "@/components/ImageUploader";

export default function HomePage() {
  return (
    <main className="flex flex-col items-center justify-center min-h-screen p-4 sm:p-8 text-center">
      <h1 className="text-4xl sm:text-5xl font-bold text-white mb-2">
        Procesador de Imágenes Serverless
      </h1>
      <p className="text-lg text-gray-300 mb-8">
        Sube una imagen y observa la magia de la computación en la nube.
      </p>
      <ImageUploader />
    </main>
  );
}