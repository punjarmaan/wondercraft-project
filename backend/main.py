from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime, timedelta
from collections import defaultdict
from pytz import timezone
import os

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.get("/")
def read_root():
    return {"message": "Hello!"}

@app.get("/subscription-growth")
async def get_subscription_growth(
    start: str = Query(..., description="Start date for the time period."),
    end: str = Query(..., description="End date for the time period.")
):

    tz = timezone("UTC")
    start_date = tz.localize(datetime.strptime(start, "%Y-%m-%d"))
    end_date = tz.localize(datetime.strptime(end, "%Y-%m-%d")) + timedelta(days=1)

    initial_subscriptions = supabase.table("user_activity").select("uid, activity").filter("time", "lt", start_date).execute()
    activities = supabase.table("user_activity").select("uid, activity, time").filter("time", "gte", start_date).filter("time", "lt", end_date).order("time", desc=False).execute()

    user_ids = list(set([str(activity["uid"]) for activity in initial_subscriptions.data] +
                    [str(activity["uid"]) for activity in activities.data]))
    
    def chunk_list(data, chunk_size):
        user_groups = []

        for i in range(0, len(data), chunk_size):
            chunk = data[i:i + chunk_size]
            query_result = (
                supabase.table("user_onboarding_data")
                .select("answer", "created_by_id")
                .filter("question", "eq", "Which of the following best describes you?")
                .in_("created_by_id", chunk)
                .execute()
            )
            user_groups.extend(query_result.data)
        
        return user_groups
    

    CHUNK_SIZE = 400
    user_group_data = chunk_list(user_ids, CHUNK_SIZE)

    user_group_map = {user["created_by_id"]: user["answer"] for user in user_group_data}
    
    subscriptions_dict = defaultdict(int)

    for activity in initial_subscriptions.data:
        uid = activity["uid"]
        group = user_group_map[uid]
        subscriptions_dict[group] += 1 if activity["activity"] == "subscription" else -1

    current_date = start_date
    next_date = current_date + timedelta(days=1)

    num_days = (end_date - start_date).days

    groups = {}
    min_subs = 0
    max_subs = 0
    dates = []

    day_ct = 0

    for activity in activities.data:
        activity_time = datetime.strptime(activity["time"], "%Y-%m-%dT%H:%M:%S.%f%z")
        activity_uid = activity["uid"]
        activity_type = activity["activity"]

        if activity_uid not in user_group_map:
            continue

        group = user_group_map[activity_uid]
        while activity_time >= next_date:
            for group_name, count in subscriptions_dict.items():
                if group_name not in groups:
                    groups[group_name] = [0] * num_days
                
                groups[group_name][day_ct] = count
                min_subs = min(min_subs, count)
                max_subs = max(max_subs, count)
            
            dates.append(current_date.strftime("%m-%d-%Y"))
            day_ct += 1
            current_date = next_date
            next_date = current_date + timedelta(days=1)
        
        subscriptions_dict[group] += 1 if activity_type == "subscription" else -1
    
    for group_name, count in subscriptions_dict.items():
        if group_name not in groups:
            groups[group_name] = [0] * num_days

        groups[group_name][day_ct] = count
        min_subs = min(min_subs, count)
        max_subs = max(max_subs, count)
    
    
    dates.append(current_date.strftime("%m-%d-%Y"))

    group_counts_by_day = []
    for i, day in enumerate(dates):
        new_day = {
            "date": day,
        }

        for group, counts in groups.items():
            new_day[group] = counts[i]
        
        group_counts_by_day.append(new_day)


    response = {
        "day_counts": group_counts_by_day,
        "min_sub": min_subs,
        "max_sub": max_subs,
        "num_days": num_days,
    }

    return response
