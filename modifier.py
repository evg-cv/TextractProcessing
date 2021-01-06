import cv2
import boto3
import configparser

from trp import Document
from settings import REF_FIELD_NAMES, TICK_THRESH

# ---------- remove --------
params = configparser.ConfigParser()
params.read("/media/main/Data/Task/TextractProcessing/config.cfg")
# ---------------


class Modifier:
    def __init__(self):
        self.net_response = None
        self.key_value_data = None
        self.frame = None
        self.table_data = None
        self.frame_width = None
        self.frame_height = None
        self.modified_data = {}
        self.textract = boto3.client('textract', region_name=params.get("DEFAULT", "region_name"),
                                     aws_access_key_id=params.get("DEFAULT", "access_key_id"),
                                     aws_secret_access_key=params.get("DEFAULT", "secret_access_key"))

    def extract_ocr_local(self, frame_path):

        # Read document content
        with open(frame_path, 'rb') as document:
            image_bytes = bytearray(document.read())

        # Call Amazon Textract
        response = self.textract.analyze_document(Document={'Bytes': image_bytes}, FeatureTypes=["TABLES", "FORMS"])

        return response

    def estimate_tick(self, origin_coord=None, next_coord=None, yes_no_ret=False, left=None, top=None, width=None,
                      bottom=None):
        if not yes_no_ret:
            roi_frame = self.frame[int((origin_coord["Top"] - 0.01) * self.frame_height):
                                   int((origin_coord["Top"] + origin_coord["Height"] - 0.003) * self.frame_height),
                                   int((origin_coord["Left"] + origin_coord["Width"] + 0.001) * self.frame_width):
                                   int(next_coord["Left"] * self.frame_width)]
        else:
            if bottom is None:
                roi_frame = self.frame[int((top - 0.01) * self.frame_height):int(top * self.frame_height),
                                       int(left * self.frame_width): int((left + width) * self.frame_width)]
            else:
                roi_frame = self.frame[int(bottom * self.frame_height):int((bottom + 0.01) * self.frame_height),
                                       int(left * self.frame_width): int((left + width) * self.frame_width)]
        # cv2.imshow("roi frame", roi_frame)
        # cv2.waitKey()
        gray_frame = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2GRAY)
        _, thresh_frame = cv2.threshold(gray_frame, 200, 255, cv2.THRESH_BINARY)
        # cv2.imshow("thresh frame", thresh_frame)
        # cv2.waitKey()
        black_pixel_nums = len(thresh_frame[thresh_frame == 0])
        print(black_pixel_nums)
        if yes_no_ret:
            return black_pixel_nums
        else:
            if black_pixel_nums > TICK_THRESH:
                return True
            else:
                return False

    def modify_table_data(self):
        current_table_coordinates = []
        init_table_coordinates = []
        for t_data in self.table_data:
            t_data_geometry = t_data.geometry.bounding_box
            current_table_coordinates.append([t_data_geometry.left, t_data_geometry.top,
                                              t_data_geometry.left + t_data_geometry.width,
                                              t_data_geometry.top + t_data_geometry.height])

        for res in self.net_response:
            res_coordinate = res["Geometry"]["BoundingBox"]
            if res["BlockType"] == "LINE" and res["Text"] == "HEAD":
                init_table_coordinates.append([res_coordinate["Left"], res_coordinate["Top"],
                                               0.5 * res_coordinate["Width"], 0.5 * res_coordinate["Height"]])
            if res["BlockType"] == "LINE" and res["Text"] == "OTHER SYMPTOMS":
                init_table_coordinates.append([res_coordinate["Left"], res_coordinate["Top"],
                                               0.5 * res_coordinate["Width"], 0.5 * res_coordinate["Height"]])
            if res["BlockType"] == "LINE" and res["Text"] == "HEAD & NECK":
                init_table_coordinates.append([res_coordinate["Left"], res_coordinate["Top"],
                                               0.5 * res_coordinate["Width"], 0.5 * res_coordinate["Height"]])
            if res["BlockType"] == "LINE" and res["Text"] == "GASTROINTESTINAL" and res_coordinate["Left"] > 0.3:
                init_table_coordinates.append([res_coordinate["Left"], res_coordinate["Top"],
                                               0.5 * res_coordinate["Width"], 0.5 * res_coordinate["Height"]])
            if res["BlockType"] == "LINE" and res["Text"] == "Criteria":
                init_table_coordinates.append([res_coordinate["Left"], res_coordinate["Top"],
                                               0.5 * res_coordinate["Width"], 0.5 * res_coordinate["Height"]])
            if res["BlockType"] == "LINE" and res["Text"] == "Other tests done":
                init_table_coordinates.append([res_coordinate["Left"], res_coordinate["Top"],
                                               0.5 * res_coordinate["Width"], 0.5 * res_coordinate["Height"]])

        modify_table_coordinates = []
        for i, i_t_coordinate in enumerate(init_table_coordinates):
            exist_ret = False
            for c_tbl_coordinate in current_table_coordinates:
                if c_tbl_coordinate[0] <= i_t_coordinate[0] + i_t_coordinate[2] <= c_tbl_coordinate[2] and \
                        c_tbl_coordinate[1] <= i_t_coordinate[1] + i_t_coordinate[3] <= c_tbl_coordinate[3]:
                    exist_ret = True
                    break
            if not exist_ret:
                if i % 2 == 0:
                    if i < len(init_table_coordinates) - 2:
                        modify_table_coordinates.append([i_t_coordinate[0] - 0.01, i_t_coordinate[1] - 0.01,
                                                         init_table_coordinates[i + 1][0] - 0.01,
                                                         init_table_coordinates[i + 2][1] - 0.01])
                    else:
                        modify_table_coordinates.append([i_t_coordinate[0] - 0.01, i_t_coordinate[1] - 0.01,
                                                         init_table_coordinates[i + 1][0] - 0.01, 1])
                else:
                    if i < len(init_table_coordinates) - 1:
                        modify_table_coordinates.append([i_t_coordinate[0] - 0.01, i_t_coordinate[1] - 0.01,
                                                         1, init_table_coordinates[i + 2][1] - 0.01])
                    else:
                        modify_table_coordinates.append([i_t_coordinate[0] - 0.01, i_t_coordinate[1] - 0.01, 1, 1])

        for idx, m_tbl_coordinate in enumerate(modify_table_coordinates):
            cv2.imwrite(f"/tmp/{idx}.jpg",
                        self.frame[int(m_tbl_coordinate[1] * self.frame_height):
                                   int(m_tbl_coordinate[3] * self.frame_height),
                                   int(m_tbl_coordinate[0] * self.frame_width):
                                   int(m_tbl_coordinate[2] * self.frame_width)])
            m_tbl_response = self.extract_ocr_local(frame_path=f"/tmp/{idx}.jpg")
            document_data = Document(response_pages=m_tbl_response)
            for table in document_data.pages[0].tables:
                csv_data = []
                for row in table.rows:
                    csv_row = []
                    for cell in row.cells:
                        csv_row.append(cell.text.strip())
                    csv_data.append(csv_row)

                print(csv_data)

                if 'Criteria' in csv_data[0]:
                    for i in range(1, len(csv_data)):
                        for j in range(1, len(csv_data[i])):
                            json_key = '{}-{}'.format(csv_data[i][0], csv_data[0][j])
                            json_val = '{}'.format(csv_data[i][j])
                            if json_key in REF_FIELD_NAMES:
                                self.modified_data[REF_FIELD_NAMES[json_key]] = json_val

                elif 'Other tests done' in csv_data[0]:
                    for i in range(1, len(csv_data)):
                        for j in range(0, len(csv_data[i])):
                            if csv_data[i][j] in REF_FIELD_NAMES:
                                json_key = '{}'.format(csv_data[i][j])
                                json_val = ''
                                try:
                                    k = j + 1
                                    json_val = '{}'.format(csv_data[i][k])
                                except Exception as e:
                                    print(e)
                                self.modified_data[REF_FIELD_NAMES[json_key]] = json_val

                else:
                    for i in range(1, len(csv_data)):
                        if csv_data[i]:
                            for j in range(0, len(csv_data[i])):
                                if csv_data[i][j] in REF_FIELD_NAMES:
                                    json_key = csv_data[i][j]
                                    for k in range(j, len(csv_data[i])):
                                        if csv_data[i][k].strip() == 'SELECTED,':
                                            self.modified_data[REF_FIELD_NAMES[json_key]] = \
                                                csv_data[0][k].replace("SELECTED", "").replace(",", "")
                                            break

        return

    def process_image(self):
        eth_s_coordinate = 0
        eth_s_confidence = 0
        eth_b_coordinate = 0
        eth_b_confidence = 0
        eth_t_coordinate = 0
        eth_t_confidence = 0
        eth_m_coordinate = 0
        eth_m_confidence = 0
        height_coordinate = 0
        prev_diag_yes = 0
        prev_diag_yes_confidence = 0
        prev_diag_no = 0
        prev_diag_no_confidence = 0
        prev_hos_yes = 0
        prev_hos_yes_confidence = 0
        prev_hos_no = 0
        prev_hos_no_confidence = 0
        for i, res in enumerate(self.net_response):
            res_coordinate = res["Geometry"]["BoundingBox"]
            if res["BlockType"] == "WORD" and "[S]" in res["Text"]:
                eth_s_coordinate = res_coordinate
                eth_s_confidence = res["Confidence"]
            if res["BlockType"] == "WORD" and "[B]" in res["Text"]:
                eth_b_coordinate = res_coordinate
                eth_b_confidence = res["Confidence"]
                height_coordinate = self.net_response[i + 1]["Geometry"]["BoundingBox"]
            if res["BlockType"] == "WORD" and "[T]" in res["Text"]:
                eth_t_coordinate = res_coordinate
                eth_t_confidence = res["Confidence"]
            if res["BlockType"] == "WORD" and "[M]" in res["Text"]:
                eth_m_coordinate = res_coordinate
                eth_m_confidence = res["Confidence"]
            if res["BlockType"] == "WORD" and "Yes" in res["Text"] and "previously" in self.net_response[i - 1]["Text"]:
                prev_diag_yes = res_coordinate
                prev_diag_yes_confidence = res["Confidence"]
            if res["BlockType"] == "WORD" and "No" in res["Text"] and "Approximate" in self.net_response[i + 1]["Text"]:
                prev_diag_no = res_coordinate
                prev_diag_no_confidence = res["Confidence"]
            if res["BlockType"] == "WORD" and "Yes" in res["Text"] and "infection" in self.net_response[i - 1]["Text"]:
                prev_hos_yes = res_coordinate
                prev_hos_yes_confidence = res["Confidence"]
            if res["BlockType"] == "WORD" and "No" in res["Text"] and "How" in self.net_response[i + 1]["Text"]:
                prev_hos_no = res_coordinate
                prev_hos_no_confidence = res["Confidence"]
        self.modified_data["ethnicity"] = ""
        if self.estimate_tick(origin_coord=eth_s_coordinate, next_coord=eth_t_coordinate):
            self.modified_data["ethnicity"] += "[S]"
            self.modified_data["ethnicity_confidence"] = eth_s_confidence
        if self.estimate_tick(origin_coord=eth_t_coordinate, next_coord=eth_m_coordinate):
            self.modified_data["ethnicity"] += "[T]"
            self.modified_data["ethnicity_confidence"] = eth_t_confidence
        if self.estimate_tick(origin_coord=eth_m_coordinate, next_coord=eth_b_coordinate):
            self.modified_data["ethnicity"] += "[M]"
            self.modified_data["ethnicity_confidence"] = eth_m_confidence
        if self.estimate_tick(origin_coord=eth_b_coordinate, next_coord=height_coordinate):
            self.modified_data["ethnicity"] += "[B]"
            self.modified_data["ethnicity_confidence"] = eth_b_confidence
        if self.estimate_tick(yes_no_ret=True, left=prev_diag_yes["Left"], width=prev_diag_yes["Width"],
                              top=prev_diag_yes["Top"]) > \
                self.estimate_tick(yes_no_ret=True, left=prev_diag_no["Left"], width=prev_diag_no["Width"],
                                   top=prev_diag_no["Top"]):
            self.modified_data["previously_diagnosed"] = "Yes"
            self.modified_data["previously_diagnosed_confidence"] = prev_diag_yes_confidence
        else:
            self.modified_data["previously_diagnosed"] = "No"
            self.modified_data["previously_diagnosed_confidence"] = prev_diag_no_confidence
        if self.estimate_tick(yes_no_ret=True, left=prev_hos_yes["Left"], width=prev_hos_yes["Width"],
                              bottom=prev_hos_yes["Top"] + prev_hos_yes["Height"] + 0.001) > \
                self.estimate_tick(yes_no_ret=True, left=prev_hos_no["Left"], width=prev_hos_no["Width"],
                                   bottom=prev_hos_no["Top"] + prev_hos_no["Height"] + 0.001):
            self.modified_data["previously_hostpitalized"] = "Yes"
            self.modified_data["previously_hostpitalized_confidence"] = prev_hos_yes_confidence
        else:
            self.modified_data["previously_hostpitalized"] = "No"
            self.modified_data["previously_hostpitalized_confidence"] = prev_hos_no_confidence

        return

    def separate_two_values(self):
        pulse_rates_index = None
        init_temp_data = None
        init_temp_data_confidence = 0
        for i, k_v_data in enumerate(self.key_value_data):
            if "Respiratory Rate" in k_v_data.key.text:
                pulse_rates_index = i
            if pulse_rates_index is not None:
                break
        for i, res in enumerate(self.net_response):
            if res["BlockType"] == "LINE" and "Temp" in res["Text"]:
                if "or" in res["Text"]:
                    init_temp_data = res["Text"].replace("Temp", "").replace(":", "")
                    init_temp_data_confidence = res["Confidence"]
                else:
                    init_temp_data = self.net_response[i + 1]["Text"]
                    init_temp_data_confidence = self.net_response[i + 1]["Confidence"]
                break

        pulse_respiratory_rates = self.key_value_data[pulse_rates_index].value.text.replace("bpm", "")
        pulse_respiratory_rates_confidence = self.key_value_data[pulse_rates_index].value.confidence
        try:
            pulse_rate, respiratory_rate = pulse_respiratory_rates.split(":")
            self.modified_data["pulse_rate"] = pulse_rate
            self.modified_data["pulse_rate_confidence"] = pulse_respiratory_rates_confidence
            self.modified_data["respritory_rate"] = respiratory_rate
            self.modified_data["respritory_rate_confidence"] = pulse_respiratory_rates_confidence
        except Exception as e:
            print(e)
            self.modified_data["pulse_rate"] = pulse_respiratory_rates
            self.modified_data["pulse_rate_confidence"] = pulse_respiratory_rates_confidence
            self.modified_data["respritory_rate"] = pulse_respiratory_rates
            self.modified_data["respritory_rate_confidence"] = pulse_respiratory_rates_confidence
        if init_temp_data is not None:
            cel_temp, fa_temp = init_temp_data.split("or")
            try:
                cel_temp = float(cel_temp.replace("0C", "").replace("-", ".").replace("°C", ""))
                self.modified_data["temperature"] = f"{cel_temp}°C"
                self.modified_data["temperature_confidence"] = init_temp_data_confidence
            except Exception as e:
                print(e)
            try:
                fa_temp = float(fa_temp.replace("0F", "").replace("-", ".").replace("°F", ""))
                self.modified_data["temperature"] = f"{fa_temp}°F"
                self.modified_data["temperature_confidence"] = init_temp_data_confidence
            except Exception as e:
                print(e)

        return

    def run(self, response, key_value_data, table_data, frame_path):
        self.net_response = response[0]["Blocks"][1:]
        self.key_value_data = key_value_data
        self.table_data = table_data
        self.frame = cv2.imread(frame_path)
        self.frame_height, self.frame_width = self.frame.shape[:2]
        self.separate_two_values()
        self.modify_table_data()
        self.process_image()

        return self.modified_data


if __name__ == '__main__':
    Modifier()
