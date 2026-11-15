#!/usr/bin/env python3
"""App Store Connect API helper for the Weekly Planner app.
Creates: bundle ID, app record, App Store provisioning profile,
internal beta group. Uses the ASC API key in ~/workspace/apps/ios/signing/.
Usage: python3 asc_planner.py <step>  (steps: bundle, app, cert, profile, group, tester)
Prints JSON results. Secrets are never printed.
"""
import json, os, sys, time, urllib.request, urllib.error
import jwt

KEY_ID = "4J8376D668"
ISSUER_ID = "ab143d75-e992-4ace-889f-c6f00048978f"
TEAM_ID = "3ADHPTL6G4"
P8 = os.path.expanduser("~/workspace/apps/ios/signing/AuthKey.p8")
BASE = "https://api.appstoreconnect.apple.com/v1"
BUNDLE_ID = "com.theammoniafiles.planner"
APP_NAME = "Weekly Planner"
SKU = "ammonia-files-planner"

def token():
    now = int(time.time())
    payload = {"iss": ISSUER_ID, "iat": now, "exp": now + 1200, "aud": "appstoreconnect-v1"}
    headers = {"alg": "ES256", "kid": KEY_ID, "typ": "JWT"}
    with open(P8) as f:
        key = f.read()
    return jwt.encode(payload, key, algorithm="ES256", headers=headers)

def call(method, path, body=None):
    req = urllib.request.Request(BASE + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": "Bearer " + token(),
                 "Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")

def main():
    step = sys.argv[1]
    if step == "bundle":
        st, r = call("GET", "/bundleIds?filter[identifier]=" + BUNDLE_ID)
        print("GET bundleIds:", st, json.dumps(r.get("data", r), indent=1)[:800])
        if r.get("data"):
            print("BUNDLE_ID_EXISTS", r["data"][0]["id"])
            return
        st, r = call("POST", "/bundleIds", {"data": {"type": "bundleIds",
            "attributes": {"identifier": BUNDLE_ID, "name": APP_NAME, "platform": "IOS"}}})
        print("POST bundleIds:", st, json.dumps(r, indent=1)[:800])
    elif step == "app":
        st, r = call("GET", "/apps?filter[bundleId]=" + BUNDLE_ID)
        print("GET apps:", st, json.dumps(r.get("data", r), indent=1)[:800])
        if r.get("data"):
            print("APP_EXISTS", r["data"][0]["id"])
            return
        st, b = call("GET", "/bundleIds?filter[identifier]=" + BUNDLE_ID)
        bid = b["data"][0]["id"]
        st, r = call("POST", "/apps", {"data": {"type": "apps",
            "attributes": {"bundleId": BUNDLE_ID, "name": APP_NAME,
                           "primaryLocale": "en-US", "sku": SKU},
            "relationships": {"bundleId": {"data": {"type": "bundleIds", "id": bid}}}}})
        print("POST apps:", st, json.dumps(r, indent=1)[:800])
    elif step == "cert":
        st, r = call("GET", "/certificates?filter[certificateType]=IOS_DISTRIBUTION&limit=10")
        print("certificates:", st)
        for c in r.get("data", []):
            a = c["attributes"]
            print(" ", c["id"], a.get("displayName"), a.get("name"), "expires:", a.get("expirationDate"))
    elif step == "profile":
        cert_id = sys.argv[2]
        st, b = call("GET", "/bundleIds?filter[identifier]=" + BUNDLE_ID)
        bid = b["data"][0]["id"]
        st, r = call("POST", "/profiles", {"data": {"type": "profiles",
            "attributes": {"name": "TAF Planner App Store", "profileType": "IOS_APP_STORE"},
            "relationships": {
                "bundleId": {"data": {"type": "bundleIds", "id": bid}},
                "certificates": {"data": [{"type": "certificates", "id": cert_id}]}}}})
        print("POST profiles:", st, json.dumps(r, indent=1)[:1200])
    elif step == "profile_get":
        pid = sys.argv[2]
        st, r = call("GET", "/profiles/" + pid)
        print("GET profile:", st, json.dumps(r, indent=1)[:600])
        if r.get("data"):
            content = r["data"]["attributes"].get("profileContent", "")
            out = os.path.expanduser("~/workspace/apps/ios/signing/planner.mobileprovision")
            open(out, "wb").write(__import__("base64").b64decode(content))
            print("saved", out, len(content), "b64 chars")
    elif step == "group":
        st, a = call("GET", "/apps?filter[bundleId]=" + BUNDLE_ID)
        app_id = a["data"][0]["id"]
        st, r = call("GET", "/apps/" + app_id + "/betaGroups")
        print("existing groups:", st, [g["attributes"]["name"] for g in r.get("data", [])])
        st, r = call("POST", "/betaGroups", {"data": {"type": "betaGroups",
            "attributes": {"name": "Internal Testers", "isInternalGroup": True},
            "relationships": {"app": {"data": {"type": "apps", "id": app_id}}}}})
        print("POST betaGroups:", st, json.dumps(r, indent=1)[:800])
    elif step == "tester":
        gid = sys.argv[2]
        st, r = call("POST", "/betaTesters", {"data": {"type": "betaTesters",
            "attributes": {"email": "bgcustom@outlook.com", "firstName": "Blake", "lastName": "Goddard"},
            "relationships": {"betaGroups": {"data": [{"type": "betaGroups", "id": gid}]}}}})
        print("POST betaTesters:", st, json.dumps(r, indent=1)[:800])
    elif step == "builds":
        st, a = call("GET", "/apps?filter[bundleId]=" + BUNDLE_ID)
        app_id = a["data"][0]["id"]
        st, r = call("GET", "/apps/" + app_id + "/builds?limit=5&sort=-uploadedDate")
        print("builds:", st)
        for b in r.get("data", []):
            print(" ", b["id"], b["attributes"].get("version"), "processing:", b["attributes"].get("processingState"),
                  "betaReview:", b["attributes"].get("betaReviewState"),
                  "usesNonExemptEncryption:", b["attributes"].get("usesNonExemptEncryption"))
    elif step == "compliance":
        build_id = sys.argv[2]
        st, r = call("PATCH", "/builds/" + build_id,
                     {"data": {"type": "builds", "id": build_id,
                               "attributes": {"usesNonExemptEncryption": False}}})
        print("PATCH builds compliance:", st, json.dumps(r, indent=1)[:600])

if __name__ == "__main__":
    main()
