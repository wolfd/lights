


void pushButton(int pin) {
  digitalWrite(pin, LOW);
  delay(50);
  digitalWrite(pin, HIGH);
  delay(200);
  digitalWrite(pin, LOW);
}

void setColor(int r, int g, int b) {
  analogWrite(9, 255 - g);
  analogWrite(10, 255 - r);
  analogWrite(11, 255 - b);
}


int getByte(){
  while(!Serial.available());
  return Serial.read();
}

void setup() {
  pinMode(9, OUTPUT);
  pinMode(10, OUTPUT);
  pinMode(11, OUTPUT);
  Serial.begin(115200);
  setColor(0,0,0);
}

void loop()
{
  while(1) {
    int r=0;
    int g=0;
    int b=0;
    
    r = getByte();
    if (r == 255)
      continue;
    else if(r == 254)
      r = 255;
      
    g = getByte();
    if (g == 255)
      continue;
    else if(g == 254)
      g = 255;
      
    b = getByte();
    if (b == 255)
      continue;
    else if(b == 254)
      b = 255;
      
    setColor(r, g, b);
  }
}

