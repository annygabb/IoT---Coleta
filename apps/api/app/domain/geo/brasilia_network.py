from typing import Dict, List, Any

# Nós principais da rede de Brasília / DF
BRASILIA_NODES: Dict[str, Dict[str, Any]] = {
    # Ponto de Descarte e Garagem SLU
    'ATERRO_SAMAMBAIA': {'id': 'ATERRO_SAMAMBAIA', 'name': 'Aterro Sanitário de Brasília', 'x': 220, 'y': 920, 'type': 'DISPOSAL', 'ra': 'Samambaia'},
    'GARAGEM_SLU': {'id': 'GARAGEM_SLU', 'name': 'Garagem Central SLU (SIA)', 'x': 740, 'y': 640, 'type': 'DEPOT', 'ra': 'SIA'},

    # Ceilândia
    'CEILANDIA_CENTRO': {'id': 'CEILANDIA_CENTRO', 'name': 'Ceilândia Centro', 'x': 180, 'y': 520, 'ra': 'Ceilândia'},
    'CEILANDIA_NORTE': {'id': 'CEILANDIA_NORTE', 'name': 'Ceilândia Norte (P-Norte)', 'x': 160, 'y': 380, 'ra': 'Ceilândia'},
    'CEILANDIA_SUL': {'id': 'CEILANDIA_SUL', 'name': 'Ceilândia Sul (Guariroba)', 'x': 240, 'y': 650, 'ra': 'Ceilândia'},

    # Taguatinga
    'TAGUA_CENTRO': {'id': 'TAGUA_CENTRO', 'name': 'Taguatinga Centro (Relógio)', 'x': 380, 'y': 620, 'ra': 'Taguatinga'},
    'TAGUA_NORTE': {'id': 'TAGUA_NORTE', 'name': 'Taguatinga Norte (Taguaparque)', 'x': 360, 'y': 440, 'ra': 'Taguatinga'},
    'TAGUA_SUL': {'id': 'TAGUA_SUL', 'name': 'Taguatinga Sul (Pistão Sul)', 'x': 390, 'y': 760, 'ra': 'Taguatinga'},

    # Samambaia
    'SAMAMBAIA_NORTE': {'id': 'SAMAMBAIA_NORTE', 'name': 'Samambaia Norte', 'x': 270, 'y': 810, 'ra': 'Samambaia'},

    # Águas Claras, Guará & Sudoeste
    'AGUAS_CLARAS': {'id': 'AGUAS_CLARAS', 'name': 'Águas Claras Boulevard', 'x': 520, 'y': 680, 'ra': 'Águas Claras'},
    'GUARA_CENTRO': {'id': 'GUARA_CENTRO', 'name': 'Guará I & II', 'x': 680, 'y': 730, 'ra': 'Guará'},
    'SUDOESTE': {'id': 'SUDOESTE', 'name': 'Sudoeste / Octogonal', 'x': 860, 'y': 600, 'ra': 'Sudoeste'},

    # Plano Piloto
    'RODOVIARIA_PLANO': {'id': 'RODOVIARIA_PLANO', 'name': 'Rodoviária do Plano Piloto', 'x': 1100, 'y': 560, 'ra': 'Plano Piloto'},
    'TORRE_TV': {'id': 'TORRE_TV', 'name': 'Torre de TV & Eixo Monumental', 'x': 1020, 'y': 560, 'ra': 'Plano Piloto'},
    'ESPLANADA': {'id': 'ESPLANADA', 'name': 'Esplanada dos Ministérios', 'x': 1260, 'y': 560, 'ra': 'Plano Piloto'},
    'CONGRESSO': {'id': 'CONGRESSO', 'name': 'Congresso & Três Poderes', 'x': 1380, 'y': 560, 'ra': 'Plano Piloto'},

    # Asa Norte & Asa Sul
    'ASA_NORTE_100': {'id': 'ASA_NORTE_100', 'name': 'Asa Norte (Quadras 100/300)', 'x': 1070, 'y': 420, 'ra': 'Plano Piloto'},
    'ASA_NORTE_400': {'id': 'ASA_NORTE_400', 'name': 'Asa Norte (Quadras 400/700)', 'x': 1040, 'y': 280, 'ra': 'Plano Piloto'},
    'ASA_NORTE_FIM': {'id': 'ASA_NORTE_FIM', 'name': 'Fim Asa Norte (Bragueto)', 'x': 1020, 'y': 160, 'ra': 'Plano Piloto'},
    
    'ASA_SUL_100': {'id': 'ASA_SUL_100', 'name': 'Asa Sul (Quadras 100/300)', 'x': 1130, 'y': 700, 'ra': 'Plano Piloto'},
    'ASA_SUL_400': {'id': 'ASA_SUL_400', 'name': 'Asa Sul (Quadras 400/700)', 'x': 1160, 'y': 840, 'ra': 'Plano Piloto'},
    'ASA_SUL_FIM': {'id': 'ASA_SUL_FIM', 'name': 'Fim Asa Sul (Aeroporto)', 'x': 1190, 'y': 980, 'ra': 'Plano Piloto'},

    # Lago Sul & Lago Norte
    'PONTE_JK': {'id': 'PONTE_JK', 'name': 'Ponte JK', 'x': 1420, 'y': 720, 'ra': 'Lago Sul'},
    'LAGO_SUL': {'id': 'LAGO_SUL', 'name': 'Lago Sul (QI / QL)', 'x': 1390, 'y': 890, 'ra': 'Lago Sul'},
    'PONTE_COSTA_SILVA': {'id': 'PONTE_COSTA_SILVA', 'name': 'Ponte Costa e Silva', 'x': 1310, 'y': 760, 'ra': 'Lago Sul'},
    'LAGO_NORTE': {'id': 'LAGO_NORTE', 'name': 'Lago Norte', 'x': 1250, 'y': 240, 'ra': 'Lago Norte'}
}

# Segmentos de vias da rede de transporte do DF
BRASILIA_ROADS: List[Dict[str, Any]] = [
    {'id': 'ROAD_ESTRUTURAL_1', 'from': 'CEILANDIA_NORTE', 'to': 'TAGUA_NORTE', 'name': 'Via Estrutural Norte', 'length_km': 12.0, 'base_speed_kmh': 80.0},
    {'id': 'ROAD_ESTRUTURAL_2', 'from': 'TAGUA_NORTE', 'to': 'SUDOESTE', 'name': 'Via Estrutural DF-095', 'length_km': 18.0, 'base_speed_kmh': 80.0},
    
    {'id': 'ROAD_EPTG_1', 'from': 'CEILANDIA_CENTRO', 'to': 'TAGUA_CENTRO', 'name': 'Av. Elmo Serejo', 'length_km': 8.0, 'base_speed_kmh': 70.0},
    {'id': 'ROAD_EPTG_2', 'from': 'TAGUA_CENTRO', 'to': 'AGUAS_CLARAS', 'name': 'EPTG - Trecho 1', 'length_km': 7.0, 'base_speed_kmh': 80.0, 'is_eptg': True},
    {'id': 'ROAD_EPTG_3', 'from': 'AGUAS_CLARAS', 'to': 'GARAGEM_SLU', 'name': 'EPTG DF-085 (Via Expressa)', 'length_km': 14.0, 'base_speed_kmh': 80.0, 'is_eptg': True},
    {'id': 'ROAD_EPTG_4', 'from': 'GARAGEM_SLU', 'to': 'SUDOESTE', 'name': 'EPTG / SIA', 'length_km': 6.0, 'base_speed_kmh': 70.0},

    {'id': 'ROAD_SAMAMBAIA_1', 'from': 'CEILANDIA_SUL', 'to': 'SAMAMBAIA_NORTE', 'name': 'Ligação Ceilândia-Samambaia', 'length_km': 6.0, 'base_speed_kmh': 60.0},
    {'id': 'ROAD_SAMAMBAIA_2', 'from': 'SAMAMBAIA_NORTE', 'to': 'ATERRO_SAMAMBAIA', 'name': 'DF-459 (Acesso Aterro)', 'length_km': 8.0, 'base_speed_kmh': 60.0, 'is_disposal': True},
    {'id': 'ROAD_SAMAMBAIA_3', 'from': 'TAGUA_SUL', 'to': 'SAMAMBAIA_NORTE', 'name': 'Boca da Mata', 'length_km': 7.0, 'base_speed_kmh': 60.0},
    {'id': 'ROAD_EPNB_1', 'from': 'TAGUA_SUL', 'to': 'GUARA_CENTRO', 'name': 'EPNB DF-075', 'length_km': 16.0, 'base_speed_kmh': 70.0},

    {'id': 'ROAD_CEIL_INT', 'from': 'CEILANDIA_NORTE', 'to': 'CEILANDIA_CENTRO', 'name': 'Hélio Prates', 'length_km': 5.0, 'base_speed_kmh': 60.0},
    {'id': 'ROAD_CEIL_INT2', 'from': 'CEILANDIA_CENTRO', 'to': 'CEILANDIA_SUL', 'name': 'Via Leste Ceilândia', 'length_km': 5.0, 'base_speed_kmh': 60.0},
    {'id': 'ROAD_TAGUA_INT1', 'from': 'TAGUA_NORTE', 'to': 'TAGUA_CENTRO', 'name': 'Comercial Norte', 'length_km': 6.0, 'base_speed_kmh': 50.0},
    {'id': 'ROAD_TAGUA_INT2', 'from': 'TAGUA_CENTRO', 'to': 'TAGUA_SUL', 'name': 'Pistão Sul DF-001', 'length_km': 6.0, 'base_speed_kmh': 60.0},
    {'id': 'ROAD_AGUAS_GUARA', 'from': 'AGUAS_CLARAS', 'to': 'GUARA_CENTRO', 'name': 'Av. das Castanheiras', 'length_km': 8.0, 'base_speed_kmh': 60.0},
    {'id': 'ROAD_GUARA_SLU', 'from': 'GUARA_CENTRO', 'to': 'GARAGEM_SLU', 'name': 'SIA Trecho 3', 'length_km': 5.0, 'base_speed_kmh': 60.0},

    {'id': 'ROAD_SUDOESTE_PLANO', 'from': 'SUDOESTE', 'to': 'TORRE_TV', 'name': 'Eixo Monumental Oeste', 'length_km': 6.0, 'base_speed_kmh': 70.0},
    {'id': 'ROAD_MONUMENTAL_1', 'from': 'TORRE_TV', 'to': 'RODOVIARIA_PLANO', 'name': 'Eixo Monumental Central', 'length_km': 4.0, 'base_speed_kmh': 60.0},
    {'id': 'ROAD_MONUMENTAL_2', 'from': 'RODOVIARIA_PLANO', 'to': 'ESPLANADA', 'name': 'Esplanada dos Ministérios', 'length_km': 5.0, 'base_speed_kmh': 60.0},
    {'id': 'ROAD_MONUMENTAL_3', 'from': 'ESPLANADA', 'to': 'CONGRESSO', 'name': 'Praça dos Três Poderes', 'length_km': 4.0, 'base_speed_kmh': 60.0},

    {'id': 'ROAD_EIXAO_N1', 'from': 'RODOVIARIA_PLANO', 'to': 'ASA_NORTE_100', 'name': 'Eixão Norte (100/300)', 'length_km': 5.0, 'base_speed_kmh': 80.0},
    {'id': 'ROAD_EIXAO_N2', 'from': 'ASA_NORTE_100', 'to': 'ASA_NORTE_400', 'name': 'Eixão Norte (400/700)', 'length_km': 6.0, 'base_speed_kmh': 80.0},
    {'id': 'ROAD_EIXAO_N3', 'from': 'ASA_NORTE_400', 'to': 'ASA_NORTE_FIM', 'name': 'Saída Norte', 'length_km': 6.0, 'base_speed_kmh': 80.0},
    {'id': 'ROAD_BRAGUETO', 'from': 'ASA_NORTE_FIM', 'to': 'LAGO_NORTE', 'name': 'Ponte do Bragueto', 'length_km': 5.0, 'base_speed_kmh': 60.0},

    {'id': 'ROAD_EIXAO_S1', 'from': 'RODOVIARIA_PLANO', 'to': 'ASA_SUL_100', 'name': 'Eixão Sul (100/300)', 'length_km': 5.0, 'base_speed_kmh': 80.0},
    {'id': 'ROAD_EIXAO_S2', 'from': 'ASA_SUL_100', 'to': 'ASA_SUL_400', 'name': 'Eixão Sul (400/700)', 'length_km': 6.0, 'base_speed_kmh': 80.0},
    {'id': 'ROAD_EIXAO_S3', 'from': 'ASA_SUL_400', 'to': 'ASA_SUL_FIM', 'name': 'Saída Sul / Aeroporto', 'length_km': 6.0, 'base_speed_kmh': 80.0},

    {'id': 'ROAD_PONTE_JK', 'from': 'ESPLANADA', 'to': 'PONTE_JK', 'name': 'Acesso Ponte JK', 'length_km': 7.0, 'base_speed_kmh': 70.0},
    {'id': 'ROAD_LAGO_JK', 'from': 'PONTE_JK', 'to': 'LAGO_SUL', 'name': 'Estrada Parque Dom Bosco', 'length_km': 6.0, 'base_speed_kmh': 60.0},
    {'id': 'ROAD_PONTE_COSTA', 'from': 'ASA_SUL_100', 'to': 'PONTE_COSTA_SILVA', 'name': 'Ponte Costa e Silva', 'length_km': 5.0, 'base_speed_kmh': 60.0},
    {'id': 'ROAD_LAGO_COSTA', 'from': 'PONTE_COSTA_SILVA', 'to': 'LAGO_SUL', 'name': 'QL 12 Lago Sul', 'length_km': 5.0, 'base_speed_kmh': 60.0},
    {'id': 'ROAD_SUL_GUARA', 'from': 'ASA_SUL_FIM', 'to': 'GUARA_CENTRO', 'name': 'EPPA / Park Way', 'length_km': 11.0, 'base_speed_kmh': 70.0}
]
