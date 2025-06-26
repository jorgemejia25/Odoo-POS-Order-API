# Funcionalidad de Extras en Órdenes POS

## Descripción

La API de órdenes POS ahora permite agregar extras a cualquier producto en una orden. Los extras son modificaciones o adicionales que:

- **NO se guardan como productos separados** en Odoo
- **SÍ impactan en el precio** total de la línea de producto
- **Aparecen en la nota del cliente** de forma legible
- **Se procesan únicamente durante la creación** de la orden

## Estructura de Datos

### Formato de Extra

Cada extra tiene la siguiente estructura:

```json
{
  "name": "Nombre del extra",
  "price": 5.0  // Opcional, por defecto 0.0
}
```

- `name` (requerido): Nombre descriptivo del extra
- `price` (opcional): Precio adicional del extra. Si no se especifica, es 0.0

### Ejemplo de Línea de Producto con Extras

```json
{
  "product_name": "Combo Brujo 2",
  "qty": 1,
  "price_unit": 30,
  "discount": 0,
  "note": "Nota base del producto",
  "extras": [
    {
      "name": "Extra queso",
      "price": 5.0
    },
    {
      "name": "Sin cebolla",
      "price": 0
    },
    {
      "name": "Papas grandes", 
      "price": 8.0
    }
  ]
}
```

## Cálculo de Precios

### Precio Unitario Final
```
precio_unitario_final = precio_base + suma_de_extras
```

Ejemplo:
- Precio base: $30.00
- Extra queso: +$5.00
- Sin cebolla: +$0.00
- Papas grandes: +$8.00
- **Precio unitario final: $43.00**

### Subtotal de Línea
```
subtotal = cantidad × precio_unitario_final × (1 - descuento/100)
```

## Formato en Nota del Cliente

Los extras se agregan automáticamente a la nota del cliente en el siguiente formato:

```
Nota base del producto
Extras: + Extra queso (+$5.00), + Sin cebolla, + Papas grandes (+$8.00)
```

### Reglas de Formato:
- Extras con precio > 0: `+ Nombre (+$precio)`
- Extras sin precio o precio = 0: `+ Nombre`
- Se concatenan con comas
- Se agregan después de la nota base con salto de línea

## Ejemplos de Uso

### 1. Producto con Extras Mixtos (con y sin costo)

```json
{
  "product_name": "Hamburguesa",
  "qty": 1,
  "price_unit": 25,
  "extras": [
    {
      "name": "Extra queso",
      "price": 3.0
    },
    {
      "name": "Sin pickles"
    },
    {
      "name": "Papas extra",
      "price": 5.0
    }
  ]
}
```

**Resultado:**
- Precio unitario: $33.00 (25 + 3 + 0 + 5)
- Nota: "Extras: + Extra queso (+$3.00), + Sin pickles, + Papas extra (+$5.00)"

### 2. Producto Solo con Extras Gratuitos

```json
{
  "product_name": "Café",
  "qty": 1,
  "price_unit": 8,
  "extras": [
    {
      "name": "Sin azúcar"
    },
    {
      "name": "Extra caliente"
    }
  ]
}
```

**Resultado:**
- Precio unitario: $8.00 (sin cambio)
- Nota: "Extras: + Sin azúcar, + Extra caliente"

### 3. Producto Solo con Extras Pagos

```json
{
  "product_name": "Pizza",
  "qty": 1,  
  "price_unit": 20,
  "extras": [
    {
      "name": "Extra pepperoni",
      "price": 4.0
    },
    {
      "name": "Extra queso",
      "price": 3.0
    }
  ]
}
```

**Resultado:**
- Precio unitario: $27.00 (20 + 4 + 3)
- Nota: "Extras: + Extra pepperoni (+$4.00), + Extra queso (+$3.00)"

## Cálculo Automático de Totales

### Funcionamiento

La API ahora calcula automáticamente el total de la orden (`amount_total`) basándose en todas las líneas de productos, incluyendo extras y descuentos.

### Campos de la Orden

#### Campos Calculados Automáticamente:
- **`amount_total`**: Suma de todos los subtotales de las líneas
- **`amount_return`**: Diferencia entre amount_paid y amount_total (si es positiva)

#### Campos Opcionales:
- **`amount_paid`**: Si no se especifica, usa el total calculado
- **`amount_tax`**: Por defecto 0.0, se puede especificar manualmente
- **`amount_return`**: Se puede especificar manualmente o se calcula automáticamente

### Ejemplos

#### 1. Orden Básica (total calculado automáticamente)
```json
{
  "partner_id": 7,
  "amount_paid": 50,
  "lines": [
    {
      "product_name": "Hamburguesa",
      "qty": 1,
      "price_unit": 25
    },
    {
      "product_name": "Papas",
      "qty": 1,
      "price_unit": 10
    }
  ]
}
```
**Resultado**: `amount_total` = 35.00, `amount_return` = 15.00

#### 2. Orden con Extras (total calculado automáticamente)
```json
{
  "partner_id": 7,
  "lines": [
    {
      "product_name": "Pizza",
      "qty": 1,
      "price_unit": 20,
      "extras": [
        {
          "name": "Extra queso",
          "price": 3.0
        }
      ]
    }
  ]
}
```
**Resultado**: `amount_total` = 23.00, `amount_paid` = 23.00, `amount_return` = 0.00

#### 3. Respuesta de la API
La API devuelve los totales calculados en la respuesta:

```json
{
  "success": true,
  "order_id": 123,
  "pos_reference": "Order 00001-001-0001",
  "calculated_totals": {
    "amount_total": 23.00,
    "amount_paid": 23.00,
    "amount_tax": 0.0,
    "amount_return": 0.00
  }
}
```

### Ventajas del Cálculo Automático

1. **Precisión**: Elimina errores de cálculo manual
2. **Simplicidad**: No necesitas calcular totales en el frontend
3. **Consistencia**: Los extras siempre se incluyen correctamente
4. **Flexibilidad**: Puedes especificar amount_paid o dejar que use el total

## Consideraciones Técnicas

1. **Validación**: Los extras con nombres vacíos se ignoran
2. **Precios**: Los precios negativos se tratan como 0
3. **Compatibilidad**: La funcionalidad es totalmente opcional - las órdenes sin extras funcionan igual que antes
4. **Rendimiento**: Los extras no requieren consultas adicionales a la base de datos
5. **Límites**: No hay límite en la cantidad de extras por producto
6. **Totales**: El cálculo automático es preciso hasta 2 decimales 