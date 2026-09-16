def test_property_gets_payment_reference_ending_in_house_number(client):
    prop = client.post("/properties", json={"identificador": "Casa 14"}).json()
    assert prop["referencia_pago"] == "0000014"


def test_two_properties_get_different_references(client):
    p1 = client.post("/properties", json={"identificador": "Depto A"}).json()
    p2 = client.post("/properties", json={"identificador": "Depto B"}).json()
    assert p1["referencia_pago"] != p2["referencia_pago"]
