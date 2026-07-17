from dataclasses import dataclass
@dataclass
class TemporalDiagnostics:
    input_frequency:str
    output_frequency:str
    alignment:str
    interpolation:str
