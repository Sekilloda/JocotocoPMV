-- 002_seed_swarm.sql
-- Seed data for Fundación de Conservación Jocotoco
-- 6 Reserves, 20 Raspberry Pi 5 Smart Monitors

-- 1. Create Jocotoco Organization
INSERT INTO organizations (id, slug, name, contact_email)
VALUES (
    'a0000000-0000-0000-0000-000000000001',
    'jocotoco-ecuador',
    'Fundación de Conservación Jocotoco',
    'conservacion@jocotoco.org.ec'
) ON CONFLICT (slug) DO NOTHING;

-- 2. Create Conservation Reserves (Projects)
INSERT INTO projects (id, organization_id, slug, name, description, reserve_code)
VALUES 
    (
        'b0000000-0000-0000-0000-000000000001',
        'a0000000-0000-0000-0000-000000000001',
        'buenaventura',
        'Reserva Biológica Buenaventura',
        'Provincia de El Oro. Hábitat del Perico de El Oro (Pyrrhura orcesi) y Colibrí Ermitaño del Chocó.',
        'RES-BUEN'
    ),
    (
        'b0000000-0000-0000-0000-000000000002',
        'a0000000-0000-0000-0000-000000000001',
        'tapichalaca',
        'Reserva Biológica Tapichalaca',
        'Provincia de Zamora-Chinchipe. Hábitat emblemático de la Grallaria ridgelyi (Jocotoco Antpitta).',
        'RES-TAPI'
    ),
    (
        'b0000000-0000-0000-0000-000000000003',
        'a0000000-0000-0000-0000-000000000001',
        'yanacocha',
        'Reserva Biológica Yanacocha',
        'Laderas del Volcán Pichincha. Bosque nublado altoandino, refugio del Zamarrito Pechinegro (Eriocnemis nigrivestis).',
        'RES-YANA'
    ),
    (
        'b0000000-0000-0000-0000-000000000004',
        'a0000000-0000-0000-0000-000000000001',
        'canande',
        'Reserva Biológica Canandé',
        'Chocó ecuatoriano en Esmeraldas. Alta biodiversidad, Cuco Terrestre Franjeado (Neomorphus radiolosus).',
        'RES-CANA'
    ),
    (
        'b0000000-0000-0000-0000-000000000005',
        'a0000000-0000-0000-0000-000000000001',
        'narupa',
        'Reserva Biológica Narupa',
        'Estribaciones amazónicas en Napo. Corredor clave para aves migratorias como Reinita Cerúlea.',
        'RES-NARU'
    ),
    (
        'b0000000-0000-0000-0000-000000000006',
        'a0000000-0000-0000-0000-000000000001',
        'antisanilla',
        'Reserva Biológica Antisanilla',
        'Páramo del Antisana. Principal dormidero y zona de anidación del Cóndor Andino (Vultur gryphus).',
        'RES-ANTI'
    )
ON CONFLICT (organization_id, slug) DO NOTHING;

-- 3. Seed Swarm of 20 Raspberry Pi 5 Monitors
INSERT INTO devices (id, organization_id, project_id, name, hardware_model, firmware_version, latitude, longitude, elevation_m, status)
VALUES
    -- Buenaventura (Pi 01 to 05)
    ('joco-rpi5-01', 'a0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000001', 'Monitor Buenaventura Quebrada', 'Raspberry Pi 5 8GB', '1.0.4', -3.6492, -79.7611, 880, 'ACTIVE'),
    ('joco-rpi5-02', 'a0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000001', 'Monitor Buenaventura Cumbre', 'Raspberry Pi 5 8GB', '1.0.4', -3.6441, -79.7580, 1020, 'ACTIVE'),
    ('joco-rpi5-03', 'a0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000001', 'Monitor Buenaventura Lek', 'Raspberry Pi 5 8GB', '1.0.4', -3.6515, -79.7645, 910, 'ACTIVE'),
    ('joco-rpi5-04', 'a0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000001', 'Monitor Buenaventura Nido 1', 'Raspberry Pi 5 8GB', '1.0.4', -3.6478, -79.7562, 940, 'ACTIVE'),
    ('joco-rpi5-05', 'a0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000001', 'Monitor Buenaventura Sendero', 'Raspberry Pi 5 8GB', '1.0.4', -3.6530, -79.7680, 850, 'ACTIVE'),

    -- Tapichalaca (Pi 06 to 09)
    ('joco-rpi5-06', 'a0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000002', 'Monitor Tapichalaca Jocotoco A', 'Raspberry Pi 5 8GB', '1.0.4', -4.4921, -79.1312, 2450, 'ACTIVE'),
    ('joco-rpi5-07', 'a0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000002', 'Monitor Tapichalaca Jocotoco B', 'Raspberry Pi 5 8GB', '1.0.4', -4.4950, -79.1290, 2520, 'ACTIVE'),
    ('joco-rpi5-08', 'a0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000002', 'Monitor Tapichalaca Mirador', 'Raspberry Pi 5 8GB', '1.0.4', -4.4890, -79.1350, 2600, 'ACTIVE'),
    ('joco-rpi5-09', 'a0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000002', 'Monitor Tapichalaca Quebrada Honda', 'Raspberry Pi 5 8GB', '1.0.4', -4.4980, -79.1275, 2380, 'ACTIVE'),

    -- Yanacocha (Pi 10 to 13)
    ('joco-rpi5-10', 'a0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000003', 'Monitor Yanacocha Zamarrito Alto', 'Raspberry Pi 5 8GB', '1.0.4', -0.1182, -78.5834, 3450, 'ACTIVE'),
    ('joco-rpi5-11', 'a0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000003', 'Monitor Yanacocha Bebederos', 'Raspberry Pi 5 8GB', '1.0.4', -0.1195, -78.5810, 3400, 'ACTIVE'),
    ('joco-rpi5-12', 'a0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000003', 'Monitor Yanacocha Bosque Polylepis', 'Raspberry Pi 5 8GB', '1.0.4', -0.1160, -78.5860, 3520, 'ACTIVE'),
    ('joco-rpi5-13', 'a0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000003', 'Monitor Yanacocha Quebrada Inca', 'Raspberry Pi 5 8GB', '1.0.4', -0.1220, -78.5790, 3320, 'ACTIVE'),

    -- Canandé (Pi 14 to 16)
    ('joco-rpi5-14', 'a0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000004', 'Monitor Canandé Dosel Chocó', 'Raspberry Pi 5 8GB', '1.0.4', 0.5281, -79.2152, 320, 'ACTIVE'),
    ('joco-rpi5-15', 'a0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000004', 'Monitor Canandé Río Guaycán', 'Raspberry Pi 5 8GB', '1.0.4', 0.5310, -79.2110, 280, 'ACTIVE'),
    ('joco-rpi5-16', 'a0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000004', 'Monitor Canandé Límite Protector', 'Raspberry Pi 5 8GB', '1.0.4', 0.5250, -79.2190, 350, 'ACTIVE'),

    -- Narupa (Pi 17 to 18)
    ('joco-rpi5-17', 'a0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000005', 'Monitor Narupa Río Hollín', 'Raspberry Pi 5 8GB', '1.0.4', -0.7254, -77.7492, 1100, 'ACTIVE'),
    ('joco-rpi5-18', 'a0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000005', 'Monitor Narupa Sendero Puma', 'Raspberry Pi 5 8GB', '1.0.4', -0.7290, -77.7460, 1150, 'ACTIVE'),

    -- Antisanilla (Pi 19 to 20)
    ('joco-rpi5-19', 'a0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000006', 'Monitor Antisanilla Peñón Cóndor', 'Raspberry Pi 5 8GB', '1.0.4', -0.4612, -78.3391, 3850, 'ACTIVE'),
    ('joco-rpi5-20', 'a0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000006', 'Monitor Antisanilla Valle Páramo', 'Raspberry Pi 5 8GB', '1.0.4', -0.4650, -78.3340, 3790, 'ACTIVE')
ON CONFLICT (id) DO UPDATE SET 
    latitude = EXCLUDED.latitude,
    longitude = EXCLUDED.longitude,
    elevation_m = EXCLUDED.elevation_m;
