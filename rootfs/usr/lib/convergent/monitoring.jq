# Rule API evidence includes recording rules and rejects startup, stalled and failed evaluations.
def epoch: sub("\\.[0-9]+Z$"; "Z") | fromdateiso8601;
# The exposition format escapes only backslash, quote and newline: control characters become spaces.
def lv: explode | map(if . < 32 or . == 127 then 32 else . end) | implode | tojson;
select(.status == "success" and (.data.groups | type == "array")) |
.data.groups as $groups |
select(($groups | length) > 0 and all($groups[]; (.rules | length) > 0)) |
[$groups[] | .interval as $interval | .rules[] |
    {ok: (.health == "ok" and ((.lastEvaluation | epoch) <= $now + 60) and
          ($now - (.lastEvaluation | epoch) < (2 * $interval + 90))),
     at: (.lastEvaluation | epoch)}] as $rules |
"cv_rules_healthy \(if all($rules[]; .ok) then 1 else 0 end)",
"cv_rules_last_evaluation_seconds \($rules | map(.at) | min)",
"cv_rules_count \($rules | length)",
($groups[] | .name as $group | .rules[] | .alerts[]? | select(.state == "firing") |
 "cv_alert_active_since_seconds{alertgroup=\($group | lv),alertname=\(.labels.alertname | lv),node=\((.labels.node // "") | lv),project=\((.labels.project // "") | lv),name=\((.labels.name // "") | lv),object=\((.labels | to_entries | sort_by(.key) | map(.key + "=" + .value) | join(", ")) | lv),severity=\((.labels.severity // "") | lv),summary=\((.annotations.summary // "") | lv),dashboard=\((.annotations.dashboard // "/d/cv-monitoring") | lv)} \(.activeAt | epoch)")
