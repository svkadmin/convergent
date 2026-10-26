def label: tojson;
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
"cv_release_status_verified{role=\($role|label),release=\($release|label)} 1",
"cv_release_status_generated_seconds{role=\($role|label),release=\($release|label)} \(.generated)",
"cv_release_advisories{role=\($role|label),release=\($release|label)} \(.advisories|length)",
(.advisories[] | "cv_release_advisory_info{role=\($role|label),release=\($release|label),target=\(.target|label),package=\(.package|label),installed_version=\(.installed_version|label),advisory=\(.advisory|label),severity=\((.severity // "unknown")|label),fixed_in=\((.fixed_in // "none")|label)} 1"),
(.packages[] | "cv_release_package_info{role=\($role|label),release=\($release|label),target=\(.target|label),package=\(.package|label),version=\(.version|label)} 1")
