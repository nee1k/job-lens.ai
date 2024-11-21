import csv
import json
import re
from os import walk

from bs4 import BeautifulSoup


def read_file(name):
    try:
        with open(name, "r", encoding="utf-8") as HTMLFile:
            htmlfiledata = HTMLFile.read()
            return BeautifulSoup(htmlfiledata, 'lxml')
    except Exception as e:
        print(f"Error reading file {name}: {e}")
        return None


def extract_job_info(file_list, verbose=True):
    job_posting_dict = []

    # Function to check if the string looks like JSON
    def is_valid_json(js):
        try:
            json.loads(js)
            return True
        except json.JSONDecodeError:
            return False

    for file in file_list:
        print(f"Reading: {file} ...")
        job_soup = read_file("ds/" + file)

        role_code = '3'  # 'ds'=1, 'DA'=2, 'BA'=3

        # Find <script> tag with type="application/ld+json"
        script_tag = job_soup.find("script", {"type": "application/ld+json"})
        if script_tag:
            js = script_tag.string.strip()
            print(f"JS Content: {js[:500]}")  # Print first 500 characters for debugging

            if is_valid_json(js):
                try:
                    json_script = json.loads(js)
                except json.JSONDecodeError as e:
                    print(f"JSON Decode Error in file {file}: {e}")
                    continue  # Skip this file and move on to the next one
            else:
                print(f"No valid JSON in file {file}, skipping.")
                continue  # Skip this file if no valid JSON found

        else:
            print(f"No relevant <script> tag found in {file}")
            continue  # Skip this file and move on to the next one

        # Extract job information from JSON-LD
        try:
            role = json_script.get("title", "Not found")
        except:
            role = "Not found"

        try:
            company = json_script.get("hiringOrganization", {}).get("name", "Not found")
        except:
            company = "Not found"

        try:
            location = json_script.get("jobLocation", {}).get("address", {}).get("addressLocality", "Not found")
        except:
            location = "Not found"

        try:
            salary_est = json_script.get("baseSalary", {}).get("value", {}).get("value", "Not found")
        except:
            salary_est = "Not found"

        try:
            education = json_script.get("educationRequirements", {}).get("credentialCategory", "Not found")
        except:
            education = "Not found"

        try:
            years_exp = json_script.get("experienceRequirements", {}).get("monthsOfExperience", "Not found")
        except:
            years_exp = "Not found"

        try:
            description_raw = json_script.get("description", "Not found")
            info = re.sub("<.*?>", " ", description_raw) if description_raw != "Not found" else description_raw
        except:
            info = "Not found"

        if verbose:
            print(f"\n<< File Name: {file} >>")
            print(f" - Role: {role}")
            print(f" - Company: {company}")
            print(f" - Location: {location}")
            print(f" - Salary Estimate: {salary_est}")
            print(f" - Education: {education}")
            print(f" - Years of Experience: {years_exp}")
            print(f" - Job Description: {info}")

        extra_info = {
            'Salary Estimate': salary_est,
            'Education': education,
            'Years of Experience': years_exp
        }

        posting = {
            'Job Role': role,
            'Role Code': role_code,
            'Company': company,
            'Location': location,
            'Job Description': info,
            'Additional Details': extra_info
        }

        print(json.dumps(posting, indent=4))
        job_posting_dict.append(posting)

    return job_posting_dict


def save_to_csv(job_posting_dict, output_file="job_postings.csv"):
    """Save job postings to a CSV file."""
    if not job_posting_dict:
        print("No job postings to save.")
        return

    # Flatten the dictionary structure for CSV compatibility
    csv_data = []
    for posting in job_posting_dict:
        flattened_posting = {
            "Job Role": posting["Job Role"],
            "Role Code": posting["Role Code"],
            "Company": posting["Company"],
            "Location": posting["Location"],
            "Job Description": posting["Job Description"],
            "Salary Estimate": posting["Additional Details"].get("Salary Estimate"),
            "Education": posting["Additional Details"].get("Education"),
            "Years of Experience": posting["Additional Details"].get("Years of Experience"),
        }
        csv_data.append(flattened_posting)

    # Write to CSV
    with open(output_file, mode="w", newline="", encoding="utf-8") as csv_file:
        fieldnames = ["Job Role", "Role Code", "Company", "Location",
                      "Job Description", "Salary Estimate", "Education",
                      "Years of Experience"]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

        writer.writeheader()  # Write header row
        writer.writerows(csv_data)  # Write all rows

    print(f"Job postings saved to {output_file}")

if __name__ == '__main__':
    file_list = []
    ## Change path
    for (dirpath, dirnames, filenames) in walk('/Users/neeleshkarthikeyan/d2i/job-lens.ai/ds'):
        file_list.extend(filenames)
        break

    # file_list is a list of saved html files from search results
    print(file_list)
    job_posting_dict = extract_job_info(file_list, verbose=False)
    print(f"Total job postings extracted: {len(job_posting_dict)}")

    # Save extracted data to CSV
    save_to_csv(job_posting_dict, output_file="job_postings.csv")