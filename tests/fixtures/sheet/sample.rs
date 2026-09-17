fn guidance(failure: &str) -> Option<&'static str> {
    match failure {
        "stateRequestFailed" => Some("서비스에 연결하지 못했습니다. 인터넷 연결을 확인한 뒤 다시 실행하십시오"),
        "stale" => Some(
            "설치된 앱이 다릅니다. 다시 설치하십시오\n\n\
             node build",
        ),
        _ => None,
    }
}

#[cfg(test)]
mod tests {
    #[test]
    fn 시험() { assert_eq!("시험 문자열입니다", "시험 문자열입니다"); }
}
