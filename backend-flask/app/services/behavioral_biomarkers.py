def interpret_biomarkers(typing_wpm: float, hesitation_ms: int, backspace_count: int, is_late_night: bool) -> float:
    """
    Digital Behavioral Biomarkers Engine
    Analyzes keyboard and timing telemetry to estimate an implicit cognitive/emotional distress score.
    Returns: distress_score (0.0 to 1.0)
    """
    distress = 0.0
    
    # Baseline comparison (assuming typical 40 WPM for casual chat)
    if typing_wpm > 0 and typing_wpm < 20: 
        # Very slow typing indicates psychomotor retardation, common in severe depression
        distress += 0.3
    
    if hesitation_ms > 10000:
        # Pausing for > 10 seconds before sending implies cognitive load, anxiety, or hesitation
        distress += 0.2
        
    if backspace_count > 15:
        # High self-correction denotes anxiety or self-doubt
        distress += 0.25
        
    if is_late_night:
        # E.g., usage between 1 AM and 5 AM implies insomnia/circadian disruption
        distress += 0.25

    return min(1.0, distress)
