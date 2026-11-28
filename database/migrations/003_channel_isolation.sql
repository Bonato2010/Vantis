-- ====================================================================
-- IAS DATABASE MIGRATION 003: MULTICHANNEL ISOLATION & PILOT CONFIG
-- Vínculo de pastas Google Drive (5 TB) para todos os 20 canais,
-- personalidades editoriais isoladas, identidades visuais e voz.
-- ====================================================================

-- 1. Garante tabela de configurações personalizadas por canal
CREATE TABLE IF NOT EXISTS channel_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id INTEGER NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
    setting_key TEXT NOT NULL,
    setting_value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(channel_id, setting_key)
);

CREATE INDEX IF NOT EXISTS idx_channel_settings_channel_key ON channel_settings(channel_id, setting_key);

-- Garante existência dos 20 canais base antes de vincular configurações
INSERT OR IGNORE INTO channels (id, channel_number, name, niche) VALUES
(1, 1, 'Canal 01', 'futebol_outros'),
(2, 2, 'Canal 02', 'casos_policiais'),
(3, 3, 'Canal 03', 'humor'),
(4, 4, 'Canal 04', 'curiosidades'),
(5, 5, 'Canal 05', 'desenvolvimento_pessoal'),
(6, 6, 'Canal 06', 'tecnologia'),
(7, 7, 'Canal 07', 'storytelling'),
(8, 8, 'Canal 08', 'humor'),
(9, 9, 'Canal 09', 'educacional'),
(10, 10, 'Canal 10', 'curiosidades'),
(11, 11, 'Canal 11', 'desenvolvimento_pessoal'),
(12, 12, 'Canal 12', 'futebol_outros'),
(13, 13, 'Canal 13', 'casos_policiais'),
(14, 14, 'Canal 14', 'tecnologia'),
(15, 15, 'Canal 15', 'cortes_podcasts'),
(16, 16, 'Canal 16', 'animacoes'),
(17, 17, 'Canal 17', 'noticias_acontecimentos'),
(18, 18, 'Canal 18', 'jogadores_esportes'),
(19, 19, 'Canal 19', 'storytelling'),
(20, 20, 'Canal 20', 'educacional');

-- 2. Atualiza pastas do Google Drive para todos os 20 canais
UPDATE channels SET gdrive_folder_id = '1Qcd6DS3zA0OrNKSeDSPTHyl_P0y0l9jf' WHERE channel_number = 1;
UPDATE channels SET gdrive_folder_id = '1fUETRbMIIjRTZyOyH_WPLNJcSUwjlPZ4' WHERE channel_number = 2;
UPDATE channels SET gdrive_folder_id = '1Eno4d315MaTNf-JCsNjpcgbNrsrsU5nb' WHERE channel_number = 3;
UPDATE channels SET gdrive_folder_id = '1wQVA6NifQrixcxVHAf9QHdqlt4g_My74' WHERE channel_number = 4;
UPDATE channels SET gdrive_folder_id = '1JoPZhLzpcmiyRRSMS0050nvYOIJfk4Z0' WHERE channel_number = 5;
UPDATE channels SET gdrive_folder_id = '1jqqsXRnLC0HOPIvPitkFgjGcbOuuTVGr' WHERE channel_number = 6;
UPDATE channels SET gdrive_folder_id = '1nOMD0G5NlN68h4YXfIpg1yAZxFtGuSJA' WHERE channel_number = 7;
UPDATE channels SET gdrive_folder_id = '1gAYSPlQxPiaK2MWduulUceYn1AHKuJVy' WHERE channel_number = 8;
UPDATE channels SET gdrive_folder_id = '1Yqc4ylr_Qm9fuuLI3hVu7UOJW0wOlOkT' WHERE channel_number = 9;
UPDATE channels SET gdrive_folder_id = '18I1FJUZcJRLtaDOstwOZadK33qX7Mey7' WHERE channel_number = 10;
UPDATE channels SET gdrive_folder_id = '1vqAqf8TGVtyFzDx2GPYvvPDGODAg-4GW' WHERE channel_number = 11;
UPDATE channels SET gdrive_folder_id = '1nBUAPvvI88tQndRpVGFbHQEpg2qhqtkt' WHERE channel_number = 12;
UPDATE channels SET gdrive_folder_id = '19b3-T6_8ChOPxXVtn9KeBqBP2ZEA3v3k' WHERE channel_number = 13;
UPDATE channels SET gdrive_folder_id = '1RDrmIE2AjEU8axWz-cDs52BJTDv2gZer' WHERE channel_number = 14;
UPDATE channels SET gdrive_folder_id = '1I3o3BQFBToloO7B6lZ7j2sPiFtOnV7c_' WHERE channel_number = 15;
UPDATE channels SET gdrive_folder_id = '1yaMYyiifXih8AY6LVK8BlLvs3Bz1VdFH' WHERE channel_number = 16;
UPDATE channels SET gdrive_folder_id = '1oc1vgvyMxHmnCYYDmnuqS_85W6sYAfHJ' WHERE channel_number = 17;
UPDATE channels SET gdrive_folder_id = '1zmqSyBaeEluusIEmNjBOu5NyBow6J6Me' WHERE channel_number = 18;
UPDATE channels SET gdrive_folder_id = '15g3CDQO5rKxyzW-DTH1UvW7abHqCLlwg' WHERE channel_number = 19;
UPDATE channels SET gdrive_folder_id = '1ZeXYV1Rg3_2DlfnJ6d7RQ9EVH1kP_Vs2' WHERE channel_number = 20;

-- 3. Configura a Identidade Editorial dos 5 Primeiros Canais Piloto

-- CANAL 01: Futebol & Paixão Nacional
UPDATE channels SET
    name = 'Canal 01 - Futebol em 60 Segundos',
    niche = 'futebol_outros',
    subniche = 'curiosidades_e_polemicas_futebol',
    target_audience = 'Torcedores e entusiastas de futebol, 18-35 anos, buscam análises passionais e lances marcantes',
    editing_style = 'Cortes dinâmicos a cada lance, slow-motion dramático no clímax, vinhetas de estádio e zooms rápidos',
    communication_tone = 'Passional, indignado, vibrante e provocativo',
    editorial_strategy = 'Polêmicas de arbitragem, jogadas geniais, rivalidades históricas e bastidores do futebol brasileiro e mundial',
    visual_identity = 'Verde e amarelo neon (#00FF66 / #FFE600), contraste alto, tipografia condensada bold'
WHERE channel_number = 1;

-- CANAL 02: Histórias & Casos Reais
UPDATE channels SET
    name = 'Canal 02 - Arquivo Sombrio (Casos Reais)',
    niche = 'casos_policiais',
    subniche = 'true_crime_e_misterios',
    target_audience = 'Fãs de investigação criminal, mistérios e true crime, 20-45 anos, focados em detalhes não revelados',
    editing_style = 'Filtro frio azulado/escuro, ritmo lento com aceleração súbita nas revelações, efeitos VHS e silêncio tenso',
    communication_tone = 'Sussurrado, tenso, conspiratório e minucioso',
    editorial_strategy = 'Casos policiais não resolvidos, reviravoltas de julgamento, pistas ignoradas pela polícia e crimes que chocaram o país',
    visual_identity = 'Preto profundo e ciano gélido (#0D1117 / #00E5FF), efeito arquivo confidencial, tipografia typewriter/mono'
WHERE channel_number = 2;

-- CANAL 03: Comédia & Situações Inusitadas
UPDATE channels SET
    name = 'Canal 03 - Rir para Não Chorar',
    niche = 'humor',
    subniche = 'situacoes_inusitadas_e_memes',
    target_audience = 'Jovens e adultos buscando alívio cômico rápido, 16-30 anos, apaixonados por humor do cotidiano',
    editing_style = 'Freeze-frames preto e branco no momento do erro, sound effects clássicos de meme, zoom cômico rápido',
    communication_tone = 'Sarcástico, espirituoso, irônico e quebras de expectativa hilárias',
    editorial_strategy = 'Momentos constrangedores do dia a dia, respostas prontas épicas e falhas humanas inusitadas capturadas em vídeo',
    visual_identity = 'Roxo e amarelo vibrante (#7B2CBF / #FFBE0B), estilo cartoon pop, tipografia arredondada com borda preta espessa'
WHERE channel_number = 3;

-- CANAL 04: Curiosidades Fascinantes & Ciência
UPDATE channels SET
    name = 'Canal 04 - Mente Curiosa & Ciência',
    niche = 'curiosidades',
    subniche = 'ciencia_do_cotidiano_e_fatos',
    target_audience = 'Público curioso, estudantes e entusiastas de ciência e tecnologia, 18-40 anos',
    editing_style = 'Gráficos limpos sobrepostos, visualização de dados em tempo real, ritmo didático de assimilação',
    communication_tone = 'Fascinado, esclarecedor, analítico e intrigante',
    editorial_strategy = 'Fenômenos científicos explicados em 45 segundos, mitos populares desmascarados e como as coisas funcionam por dentro',
    visual_identity = 'Azul elétrico e verde menta (#2563EB / #10B981), overlays de esquemas técnicos, tipografia sans-serif limpa'
WHERE channel_number = 4;

-- CANAL 05: Desenvolvimento Pessoal & Produtividade
UPDATE channels SET
    name = 'Canal 05 - Mente Focada & Produtividade',
    niche = 'desenvolvimento_pessoal',
    subniche = 'habitos_e_disciplina',
    target_audience = 'Jovens profissionais, empreendedores e estudantes buscando alta performance e disciplina diária',
    editing_style = 'Cortes cirúrgicos secos, cronômetro na tela, pausas de impacto sem palavras supérfluas',
    communication_tone = 'Direto, sem desculpas, disciplinado e transformador',
    editorial_strategy = 'Técnicas de sono, eliminação de procrastinação, psicologia do foco e rotinas de alta performance',
    visual_identity = 'Preto minimalista com detalhes em vermelho (#000000 / #FFFFFF / #EF4444), tipografia bold geométrica'
WHERE channel_number = 5;

-- 4. Insere Configurações Detalhadas de Branding, Legendas e Voz dos Canais Piloto

-- Canal 1 Settings
INSERT OR REPLACE INTO channel_settings (channel_id, setting_key, setting_value, updated_at) VALUES
(1, 'archetype_slug', 'fanatico_futebol', CURRENT_TIMESTAMP),
(1, 'wpm_target', '170', CURRENT_TIMESTAMP),
(1, 'brand_colors', '{"primary": "#00FF66", "secondary": "#FFE600", "background": "#001E0A", "highlight": "#FFFFFF"}', CURRENT_TIMESTAMP),
(1, 'subtitle_style', '{"font": "Arial Black", "fontsize": 80, "primary_colour": "&H0000FFFF&", "outline_colour": "&H00000000&", "bold": 1, "outline": 4}', CURRENT_TIMESTAMP),
(1, 'voice_profile', '{"engine": "edge-tts", "voice_id": "pt-BR-AntonioNeural", "rate": "+15%", "pitch": "+0Hz"}', CURRENT_TIMESTAMP),
(1, 'catchphrases', '["Isso aqui não é futebol, é aula!", "Comente se você acha que foi roubado.", "Respeita a história desse craque."]', CURRENT_TIMESTAMP);

-- Canal 2 Settings
INSERT OR REPLACE INTO channel_settings (channel_id, setting_key, setting_value, updated_at) VALUES
(2, 'archetype_slug', 'investigador_misterios', CURRENT_TIMESTAMP),
(2, 'wpm_target', '140', CURRENT_TIMESTAMP),
(2, 'brand_colors', '{"primary": "#00E5FF", "secondary": "#6C757D", "background": "#0D1117", "highlight": "#FF0055"}', CURRENT_TIMESTAMP),
(2, 'subtitle_style', '{"font": "Consolas", "fontsize": 72, "primary_colour": "&H00FFFF00&", "outline_colour": "&H00000000&", "bold": 1, "outline": 3}', CURRENT_TIMESTAMP),
(2, 'voice_profile', '{"engine": "edge-tts", "voice_id": "pt-BR-JulioNeural", "rate": "-5%", "pitch": "-5Hz"}', CURRENT_TIMESTAMP),
(2, 'catchphrases', '["O detalhe que passou despercebido por todos.", "Quem estava mentindo desde o começo?", "A resposta sempre esteve aqui."]', CURRENT_TIMESTAMP);

-- Canal 3 Settings
INSERT OR REPLACE INTO channel_settings (channel_id, setting_key, setting_value, updated_at) VALUES
(3, 'archetype_slug', 'comediante_acido', CURRENT_TIMESTAMP),
(3, 'wpm_target', '160', CURRENT_TIMESTAMP),
(3, 'brand_colors', '{"primary": "#FFBE0B", "secondary": "#7B2CBF", "background": "#1A002C", "highlight": "#FB5607"}', CURRENT_TIMESTAMP),
(3, 'subtitle_style', '{"font": "Impact", "fontsize": 85, "primary_colour": "&H0000FFFF&", "outline_colour": "&H002C007B&", "bold": 1, "outline": 5}', CURRENT_TIMESTAMP),
(3, 'voice_profile', '{"engine": "edge-tts", "voice_id": "pt-BR-FabioNeural", "rate": "+10%", "pitch": "+5Hz"}', CURRENT_TIMESTAMP),
(3, 'catchphrases', '["Simplesmente genial, só que ao contrário.", "Se eu não tivesse gravado ninguém acreditaria.", "Parabéns aos envolvidos."]', CURRENT_TIMESTAMP);

-- Canal 4 Settings
INSERT OR REPLACE INTO channel_settings (channel_id, setting_key, setting_value, updated_at) VALUES
(4, 'archetype_slug', 'cientista_curioso', CURRENT_TIMESTAMP),
(4, 'wpm_target', '155', CURRENT_TIMESTAMP),
(4, 'brand_colors', '{"primary": "#10B981", "secondary": "#2563EB", "background": "#0A192F", "highlight": "#FACC15"}', CURRENT_TIMESTAMP),
(4, 'subtitle_style', '{"font": "Trebuchet MS", "fontsize": 75, "primary_colour": "&H00FFFFFF&", "outline_colour": "&H00EB6325&", "bold": 1, "outline": 3}', CURRENT_TIMESTAMP),
(4, 'voice_profile', '{"engine": "edge-tts", "voice_id": "pt-BR-FranciscaNeural", "rate": "+5%", "pitch": "+0Hz"}', CURRENT_TIMESTAMP),
(4, 'catchphrases', '["Isso tem uma explicação matemática.", "Parece mágica, mas é física pura.", "Aposto que nunca te ensinaram isso na escola."]', CURRENT_TIMESTAMP);

-- Canal 5 Settings
INSERT OR REPLACE INTO channel_settings (channel_id, setting_key, setting_value, updated_at) VALUES
(5, 'archetype_slug', 'guru_produtividade', CURRENT_TIMESTAMP),
(5, 'wpm_target', '160', CURRENT_TIMESTAMP),
(5, 'brand_colors', '{"primary": "#EF4444", "secondary": "#FFFFFF", "background": "#000000", "highlight": "#F97316"}', CURRENT_TIMESTAMP),
(5, 'subtitle_style', '{"font": "Arial Black", "fontsize": 78, "primary_colour": "&H00FFFFFF&", "outline_colour": "&H00000000&", "bold": 1, "outline": 4}', CURRENT_TIMESTAMP),
(5, 'voice_profile', '{"engine": "edge-tts", "voice_id": "pt-BR-ValerioNeural", "rate": "+8%", "pitch": "-2Hz"}', CURRENT_TIMESTAMP),
(5, 'catchphrases', '["A dor da disciplina ou a dor do arrependimento.", "Menos desculpas, mais execução.", "Faça isso antes das 8 da manhã."]', CURRENT_TIMESTAMP);
