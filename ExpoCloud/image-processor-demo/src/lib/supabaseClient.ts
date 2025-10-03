// lib/supabaseClient.ts

/**
 * Este archivo crea y exporta un cliente de Supabase.
 * Utiliza las variables de entorno para la URL y la clave anónima (anon key),
 * asegurando que las credenciales no estén expuestas en el código fuente.
 * Este cliente se puede importar en cualquier componente para interactuar
 * con los servicios de Supabase (Base de datos, Almacenamiento, etc.).
 */

import { createClient, SupabaseClient } from '@supabase/supabase-js';

const supabaseUrl: string = process.env.NEXT_PUBLIC_SUPABASE_URL as string;
const supabaseAnonKey: string = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY as string;

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error("Faltan variables de entorno: NEXT_PUBLIC_SUPABASE_URL o NEXT_PUBLIC_SUPABASE_ANON_KEY");
}

export const supabase: SupabaseClient = createClient(supabaseUrl, supabaseAnonKey);
