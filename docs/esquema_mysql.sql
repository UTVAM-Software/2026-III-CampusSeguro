-- Esquema de Campus Seguro en MySQL.
--
-- GENERADO: no se edita a mano. Sale de los modelos de Django con
--     python herramientas/generar_esquema_mysql.py
--
-- El proyecto corre sobre SQLite; esto existe para ver el diagrama en
-- MySQL Workbench, con Database > Reverse Engineer MySQL Create Script.
--
-- 12 tablas del proyecto. Las de Django (django_migrations,
-- auth_permission y demas) no estan aqui: son del framework, no del
-- modelo del negocio.

-- La base se llama ...-diagrama y NO campus_seguro a proposito: en esta
-- maquina ya hay un MySQL con una base campus_seguro, la del proyecto
-- anterior. Importar esto ahi le meteria once tablas encima.
CREATE DATABASE IF NOT EXISTS campus_seguro_diagrama
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE campus_seguro_diagrama;

-- Campus
CREATE TABLE `campus_campus` (
  `id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY,
  `nombre` varchar(100) NOT NULL,
  `direccion` varchar(200) NOT NULL,
  `latitud` numeric(9, 6) NOT NULL,
  `longitud` numeric(9, 6) NOT NULL,
  `activo` bool NOT NULL,
  `dominios_correo` varchar(200) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Puntos de apoyo
CREATE TABLE `campus_puntoapoyo` (
  `id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY,
  `campus_id` bigint NOT NULL,
  `nombre` varchar(100) NOT NULL,
  `tipo` varchar(20) NOT NULL,
  `descripcion` longtext NOT NULL,
  `latitud` numeric(9, 6) NOT NULL,
  `longitud` numeric(9, 6) NOT NULL,
  `horario` varchar(100) NOT NULL,
  `activo` bool NOT NULL,
  CONSTRAINT `fk_campus_puntoapoyo_campus_id` FOREIGN KEY (`campus_id`) REFERENCES `campus_campus` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- usuarios
CREATE TABLE `usuarios_usuario` (
  `id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY,
  `password` varchar(128) NOT NULL,
  `last_login` datetime(6) NULL,
  `nombre` varchar(100) NOT NULL,
  `apellidos` varchar(100) NOT NULL,
  `correo` varchar(254) NOT NULL UNIQUE,
  `telefono` varchar(15) NOT NULL,
  `rol` varchar(20) NOT NULL,
  `foto` varchar(500) NOT NULL,
  `campus_id` bigint NULL,
  `activo` bool NOT NULL,
  `fecha_registro` datetime(6) NOT NULL,
  CONSTRAINT `fk_usuarios_usuario_campus_id` FOREIGN KEY (`campus_id`) REFERENCES `campus_campus` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- reportes
CREATE TABLE `reportes_reporte` (
  `id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY,
  `usuario_id` bigint NOT NULL,
  `campus_id` bigint NOT NULL,
  `tipo` varchar(20) NOT NULL,
  `descripcion` longtext NOT NULL,
  `latitud` numeric(9, 6) NOT NULL,
  `longitud` numeric(9, 6) NOT NULL,
  `foto` varchar(100) NOT NULL,
  `estado` varchar(20) NOT NULL,
  `fecha_creacion` datetime(6) NOT NULL,
  CONSTRAINT `fk_reportes_reporte_usuario_id` FOREIGN KEY (`usuario_id`) REFERENCES `usuarios_usuario` (`id`),
  CONSTRAINT `fk_reportes_reporte_campus_id` FOREIGN KEY (`campus_id`) REFERENCES `campus_campus` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Confirmaciones de reporte
CREATE TABLE `reportes_reporteconfirmacion` (
  `id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY,
  `reporte_id` bigint NOT NULL,
  `usuario_id` bigint NOT NULL,
  `confirma` bool NOT NULL,
  `comentario` varchar(200) NOT NULL,
  `fecha` datetime(6) NOT NULL,
  CONSTRAINT `fk_reportes_reporteconfirmacion_reporte_id` FOREIGN KEY (`reporte_id`) REFERENCES `reportes_reporte` (`id`),
  CONSTRAINT `fk_reportes_reporteconfirmacion_usuario_id` FOREIGN KEY (`usuario_id`) REFERENCES `usuarios_usuario` (`id`),
  UNIQUE KEY `uq_reportes_reporteconfirmacion` (`reporte_id`, `usuario_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- viajes
CREATE TABLE `viajes_viaje` (
  `id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY,
  `usuario_id` bigint NOT NULL,
  `origen` varchar(150) NOT NULL,
  `destino` varchar(150) NOT NULL,
  `latitud_origen` numeric(9, 6) NULL,
  `longitud_origen` numeric(9, 6) NULL,
  `latitud_destino` numeric(9, 6) NULL,
  `longitud_destino` numeric(9, 6) NULL,
  `estado` varchar(20) NOT NULL,
  `fecha_inicio` datetime(6) NOT NULL,
  `fecha_fin` datetime(6) NULL,
  `fecha_expiracion` datetime(6) NULL,
  CONSTRAINT `fk_viajes_viaje_usuario_id` FOREIGN KEY (`usuario_id`) REFERENCES `usuarios_usuario` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Acompañantes de viaje
CREATE TABLE `viajes_viajeacompanante` (
  `id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY,
  `viaje_id` bigint NOT NULL,
  `acompanante_id` bigint NOT NULL,
  `estado` varchar(20) NOT NULL,
  CONSTRAINT `fk_viajes_viajeacompanante_viaje_id` FOREIGN KEY (`viaje_id`) REFERENCES `viajes_viaje` (`id`),
  CONSTRAINT `fk_viajes_viajeacompanante_acompanante_id` FOREIGN KEY (`acompanante_id`) REFERENCES `usuarios_usuario` (`id`),
  UNIQUE KEY `uq_viajes_viajeacompanante` (`viaje_id`, `acompanante_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Ubicaciones de viaje
CREATE TABLE `viajes_ubicacionviaje` (
  `id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY,
  `viaje_id` bigint NOT NULL,
  `latitud` numeric(9, 6) NOT NULL,
  `longitud` numeric(9, 6) NOT NULL,
  `fecha_registro` datetime(6) NOT NULL,
  CONSTRAINT `fk_viajes_ubicacionviaje_viaje_id` FOREIGN KEY (`viaje_id`) REFERENCES `viajes_viaje` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Destinos guardados
CREATE TABLE `viajes_destinoguardado` (
  `id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY,
  `usuario_id` bigint NOT NULL,
  `etiqueta` varchar(40) NOT NULL,
  `referencia` varchar(200) NOT NULL,
  `latitud` numeric(9, 6) NOT NULL,
  `longitud` numeric(9, 6) NOT NULL,
  `fecha_creacion` datetime(6) NOT NULL,
  CONSTRAINT `fk_viajes_destinoguardado_usuario_id` FOREIGN KEY (`usuario_id`) REFERENCES `usuarios_usuario` (`id`),
  UNIQUE KEY `uq_viajes_destinoguardado` (`usuario_id`, `etiqueta`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Notificaciones
CREATE TABLE `comunicacion_notificacion` (
  `id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY,
  `usuario_id` bigint NOT NULL,
  `titulo` varchar(100) NOT NULL,
  `mensaje` longtext NOT NULL,
  `leida` bool NOT NULL,
  `fecha` datetime(6) NOT NULL,
  CONSTRAINT `fk_comunicacion_notificacion_usuario_id` FOREIGN KEY (`usuario_id`) REFERENCES `usuarios_usuario` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- avisos
CREATE TABLE `comunicacion_aviso` (
  `id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY,
  `campus_id` bigint NOT NULL,
  `autor_id` bigint NULL,
  `titulo` varchar(100) NOT NULL,
  `contenido` longtext NOT NULL,
  `nivel` varchar(20) NOT NULL,
  `fecha_publicacion` datetime(6) NOT NULL,
  `fecha_expiracion` date NULL,
  `activo` bool NOT NULL,
  CONSTRAINT `fk_comunicacion_aviso_campus_id` FOREIGN KEY (`campus_id`) REFERENCES `campus_campus` (`id`),
  CONSTRAINT `fk_comunicacion_aviso_autor_id` FOREIGN KEY (`autor_id`) REFERENCES `usuarios_usuario` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Correcciones de puntos de apoyo
CREATE TABLE `campus_correccion` (
  `id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY,
  `punto_id` bigint NOT NULL,
  `usuario_id` bigint NOT NULL,
  `motivo` varchar(20) NOT NULL,
  `comentario` varchar(300) NOT NULL,
  `fecha` datetime(6) NOT NULL,
  `atendida` bool NOT NULL,
  `fecha_atendida` datetime(6) NULL,
  CONSTRAINT `fk_campus_correccion_punto_id` FOREIGN KEY (`punto_id`) REFERENCES `campus_puntoapoyo` (`id`),
  CONSTRAINT `fk_campus_correccion_usuario_id` FOREIGN KEY (`usuario_id`) REFERENCES `usuarios_usuario` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
