"""One-shot CPU/GPU worker: release model memory when a request completes."""

import contextlib
import json
import sys


def main():
    request = json.load(sys.stdin)
    with contextlib.redirect_stdout(sys.stderr):
        from laya import Agent
        context = request["context"]
        path = request.get("model_path") or request["checkpoint"]
        agent = Agent(path, device=request.get("device", "cpu"), revision=request.get("revision"))
        options = {o["id"]: o["label"] + " " + o.get("notes", "") for o in context["options"]}
        state = json.dumps(context, ensure_ascii=False)
        questions = {"selection": {"type": "choice", "instructions":
            "根据用户目标、截止时间与约束，哪个选项最符合成功标准？", "criteria": options}}
        result = agent.predict(state, questions)
        if result.get("usage", {}).get("truncated") or result.get("usage", {}).get("options"):
            print(json.dumps({"error": "Laya输入超出完整比较的预算，请缩短背景和选项或改用Ollama"}), file=sys.__stdout__)
            return
        answer = result["answers"]["selection"]
    output = {"answer": {"option_id": answer["choice"], "confidence": answer["confidence"],
        "rationale": "Laya根据当前问题与选项进行了类型化比较。它不生成解释；请对照成功标准核查，分数未在个人任务上校准。"},
        "metadata": {"checkpoint": request["checkpoint"], "revision": request.get("revision"), "laya_version": "0.4.14",
                     "usage": result.get("usage", {}), "probabilities": answer.get("probabilities"),
                     "device": request.get("device", "cpu"), "output_kind": "choice"}}
    print(json.dumps(output, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
