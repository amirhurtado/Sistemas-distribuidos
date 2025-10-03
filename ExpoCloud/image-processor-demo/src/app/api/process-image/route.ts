
import { supabase } from '@/lib/supabaseClient';
import sharp from 'sharp';

/**
 * Esta es una Ruta de API de Next.js que actúa como una Función Serverless.
 * Se encarga de procesar una imagen que ya ha sido subida a Supabase Storage.
 *
 * @param {Request} request - El objeto de la solicitud entrante.
 * @returns {Response} - Una respuesta JSON con la URL de la imagen procesada o un error.
 */
export async function POST(request: Request) {
  try {
    // 1. Extraer la ruta del archivo del cuerpo de la solicitud
    const { filePath } = await request.json();
    if (!filePath) {
      return new Response(JSON.stringify({ error: 'Falta la ruta del archivo (filePath).' }), { status: 400 });
    }

    // --- TAREA 1: DESCARGAR LA IMAGEN ORIGINAL ---
    const { data: downloadData, error: downloadError } = await supabase.storage
      .from('images')
      .download(filePath);

    if (downloadError) {
      console.error('Error al descargar la imagen:', downloadError);
      return new Response(JSON.stringify({ error: 'No se pudo descargar la imagen original.' }), { status: 500 });
    }

    // --- TAREA 2: PROCESAR LA IMAGEN CON SHARP ---
    // Convertimos la imagen a un buffer, la pasamos a escala de grises y la preparamos para subirla
    const imageBuffer = Buffer.from(await downloadData.arrayBuffer());
    const processedImageBuffer = await sharp(imageBuffer)
      .grayscale() // ¡La magia sucede aquí!
      .png() // Convertimos a PNG para consistencia
      .toBuffer();

    // --- TAREA 3: SUBIR LA IMAGEN PROCESADA ---
    const newFilePath = `processed/${Date.now()}-processed.png`;

    const { error: uploadError } = await supabase.storage
      .from('images')
      .upload(newFilePath, processedImageBuffer, {
        contentType: 'image/png',
        upsert: false, // No sobrescribir si ya existe
      });

    if (uploadError) {
      console.error('Error al subir la imagen procesada:', uploadError);
      return new Response(JSON.stringify({ error: 'No se pudo subir la imagen procesada.' }), { status: 500 });
    }

    // Obtener la URL pública de la imagen recién procesada
    const { data: { publicUrl } } = supabase.storage
      .from('images')
      .getPublicUrl(newFilePath);

    // Si todo fue exitoso, devolver la URL de la imagen procesada
    return new Response(JSON.stringify({ processedUrl: publicUrl }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });

  } catch (e) {
    console.error('Error inesperado en la función:', e);
    return new Response(JSON.stringify({ error: 'Ocurrió un error en el servidor.' }), { status: 500 });
  }
}