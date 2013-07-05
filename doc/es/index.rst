===============================
Fecha de la factura correlativa
===============================

Este módulo previene la creación de facturas con una fecha anterior a la fecha
de la última factura. Sólo comprueba las facturas de cliente y de devolución.

Es importante que la numeración de las facturas contengan el mismo número de carácteres.
En la configuración de la secuencia es importante que genere el número de facturas añadiendo
zeros como prefijo para que la numeración sea correlativa. Ejemplo:

 * 00001
 * 00002
 * ...
 * 00200
 * 00201
 * ...
