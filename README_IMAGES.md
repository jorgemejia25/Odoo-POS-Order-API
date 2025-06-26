# Funcionalidad de Imágenes en la API de Productos

## Descripción

La API de productos ahora incluye URLs de imágenes en las respuestas de los endpoints para obtener y crear productos. Esto permite a los clientes acceder directamente a las imágenes de los productos a través de URLs generadas automáticamente.

## Endpoints Actualizados

### 1. Obtener Producto por Nombre
**GET** `/api/pos/get_product_by_name`

#### Parámetros:
- `product_name` (requerido): Nombre del producto a buscar
- `image_size` (opcional): Tamaño de la imagen (por defecto: '1920')

#### Ejemplo de Solicitud:
```http
GET /api/pos/get_product_by_name?product_name=Combo Brujo 2&image_size=512
```

#### Ejemplo de Respuesta:
```json
{
  "success": true,
  "product_id": 123,
  "name": "Combo Brujo 2 D",
  "list_price": 30.0,
  "image_url": "http://localhost:8069/web/image/product.product/123/image_512"
}
```

### 2. Obtener o Crear Producto
**GET/POST** `/api/pos/get_or_create_product`

#### Parámetros GET:
- `product_name` (requerido): Nombre del producto
- `price_unit` (opcional): Precio del producto
- `image_size` (opcional): Tamaño de la imagen (por defecto: '1920')

#### Parámetros POST (JSON):
```json
{
  "product_name": "Producto Ejemplo",
  "price_unit": 25.0,
  "image_size": "512"
}
```

#### Ejemplo de Respuesta:
```json
{
  "success": true,
  "product_id": 124,
  "name": "Producto Ejemplo D",
  "list_price": 25.0,
  "image_url": "http://localhost:8069/web/image/product.product/124/image_512"
}
```

## Tamaños de Imagen Disponibles

La API soporta los siguientes tamaños de imagen estándar de Odoo:

- **1920**: Imagen en alta resolución (por defecto)
- **1024**: Imagen en resolución media-alta
- **512**: Imagen en resolución media
- **256**: Imagen en resolución baja
- **128**: Imagen en miniatura

## Formato de URL de Imagen

Las URLs de imagen siguen el patrón estándar de Odoo:
```
{base_url}/web/image/product.product/{product_id}/image_{size}
```

### Ejemplos:
- `http://localhost:8069/web/image/product.product/123/image_1920`
- `http://localhost:8069/web/image/product.product/123/image_512`
- `http://localhost:8069/web/image/product.product/123/image_256`

## Comportamiento de Imágenes

### Productos Nuevos
Los productos creados automáticamente por la API pueden no tener imágenes asignadas inicialmente. En este caso:
- La URL se genera correctamente
- Si no hay imagen, Odoo devuelve una imagen por defecto o transparente
- Las imágenes pueden agregarse posteriormente a través de la interfaz de Odoo

### Productos Existentes
Para productos que ya tienen imágenes:
- La URL devuelve la imagen real del producto
- Los diferentes tamaños se generan automáticamente por Odoo
- Las imágenes se almacenan en el sistema de archivos de Odoo

## Autenticación

Las URLs de imagen generadas **requieren autenticación** de Odoo para acceder a las imágenes. Si necesitas acceso público a las imágenes, considera:

1. **Configurar acceso público** en Odoo (no recomendado para producción)
2. **Descargar y servir las imágenes** desde tu propia aplicación
3. **Usar un proxy** que maneje la autenticación automáticamente

## Ejemplo de Uso Completo

### 1. Obtener producto con imagen en tamaño medio
```http
GET /api/pos/get_product_by_name?product_name=Pizza Mediana&image_size=512
Cookie: session_id=tu_session_id_aqui
```

**Respuesta:**
```json
{
  "success": true,
  "product_id": 456,
  "name": "Pizza Mediana D",
  "list_price": 25.0,
  "image_url": "http://localhost:8069/web/image/product.product/456/image_512"
}
```

### 2. Crear producto y obtener URL de imagen
```http
POST /api/pos/get_or_create_product
Content-Type: application/json
Cookie: session_id=tu_session_id_aqui

{
  "product_name": "Hamburguesa Especial",
  "price_unit": 18.5,
  "image_size": "256"
}
```

**Respuesta:**
```json
{
  "success": true,
  "product_id": 789,
  "name": "Hamburguesa Especial D",
  "list_price": 18.5,
  "image_url": "http://localhost:8069/web/image/product.product/789/image_256"
}
```

## Consideraciones Técnicas

1. **Performance**: Los tamaños más pequeños (128, 256) se cargan más rápido
2. **Calidad**: Los tamaños más grandes (1920, 1024) ofrecen mejor calidad
3. **Cache**: Odoo maneja automáticamente el cache de las imágenes
4. **Fallback**: Si no existe la imagen, Odoo puede devolver una imagen por defecto
5. **Seguridad**: Las URLs respetan los permisos de acceso configurados en Odoo

## Casos de Uso Recomendados

- **Lista de productos**: Usar tamaño 256 o 512 para cargas rápidas
- **Vista detallada**: Usar tamaño 1024 o 1920 para mejor calidad
- **Miniaturas**: Usar tamaño 128 para previsualizaciones
- **Aplicaciones móviles**: Usar tamaños 256 o 512 para optimizar el ancho de banda 