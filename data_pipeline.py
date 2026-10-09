# Data Pipeline: cleans raw input before it's saved or sent to the RAG


# User Input Data

def injury_input(injury_type, pain_level, pain_symptoms, recovery_log, exercise_log):

    return {
        "injury_type": (injury_type or "").lower().strip(),
        "pain_level": int(pain_level),
        "pain_symptoms": (pain_symptoms or "").lower().strip(),
        "recovery_log": (recovery_log or "").lower().strip(),
        "exercise_log": (exercise_log or "").lower().strip()
    }


# Insurance Data

def insurance_input(injury_category, expected_injury_duration, historical_recovery_data, recovery_status):

    return {
        "injury_category": (injury_category or "").lower().strip(),
        "expected_injury_duration": int(expected_injury_duration),
        "historical_recovery_data": historical_recovery_data,
        "recovery_status": (recovery_status or "").lower().strip()
    }


# PT Exercise Library

def exercise_library(exercise_title, muscle_target, exercise_difficulty, exercise_set, exercise_rep, equipment_needed):

    return {
        "exercise_title": (exercise_title or "").lower().strip(),
        "muscle_target": (muscle_target or "").lower().strip(),
        "exercise_difficulty": (exercise_difficulty or "").lower().strip(),
        "exercise_set": int(exercise_set),
        "exercise_reps": int(exercise_rep),
        "equipment_needed": (equipment_needed or "").lower().strip()
    }