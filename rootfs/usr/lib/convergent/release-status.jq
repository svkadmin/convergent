def lv: tojson;
def short: type == "string" and length > 0 and length <= 256 and (explode | all(. >= 32 and . != 127));
if length != 1 then error("expected one status document") else .[0] end |
if .release != $release or (.generated | type) != "number" or
   .generated != (.generated | floor) or .generated < 0 or .generated > ($now + 300) or
   .generated < $previous or
   (.advisories | type) != "array" or (.advisories | length) > 4096 or
   (.packages | type) != "array" or (.packages | length) > 128 or
   (all(.advisories[]; (.target | short) and (.package | short) and
        (.installed_version | short) and (.advisory | short) and
        (.severity == null or (.severity | short)) and (.fixed_in == null or (.fixed_in | short))) | not) or
   (all(.packages[]; (.target | short) and (.package | short) and (.version | short)) | not)
then error("invalid advisory status") else . end |
"cv_release_status_verified{role=\($role|lv),release=\($release|lv)} 1",
"cv_release_status_generated_seconds{role=\($role|lv),release=\($release|lv)} \(.generated)",
"cv_release_advisories{role=\($role|lv),release=\($release|lv)} \(.advisories|length)",
(.advisories[] | "cv_release_advisory_info{role=\($role|lv),release=\($release|lv),target=\(.target|lv),package=\(.package|lv),installed_version=\(.installed_version|lv),advisory=\(.advisory|lv),severity=\((.severity // "unknown")|lv),fixed_in=\((.fixed_in // "none")|lv)} 1"),
(.packages[] | "cv_release_package_info{role=\($role|lv),release=\($release|lv),target=\(.target|lv),package=\(.package|lv),version=\(.version|lv)} 1")
