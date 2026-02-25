pub fn levenshtein_cmp(text1: &str, text2: &str, threshold: f64) -> bool {
    let t1 = text1.split_whitespace().collect::<Vec<_>>().join(" ").to_lowercase();
    let t2 = text2.split_whitespace().collect::<Vec<_>>().join(" ").to_lowercase();
    
    if t1.is_empty() || t2.is_empty() {
        return false;
    }
    
    // Простая метрика схожести
    let similarity = if t1.len() > t2.len() {
        t2.len() as f64 / t1.len() as f64
    } else {
        t1.len() as f64 / t2.len() as f64
    };
    
    similarity >= threshold
}